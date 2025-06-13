"""OKX API client adapter implementation.

This adapter handles all communication with the OKX API,
including authentication and data fetching.
"""
import base64
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlencode

from rotki2.exchanges.common.auth import HmacSigner, HashAlgorithm, Encoding
from rotki2.exchanges.common.client import GenericApiClient
from rotki2.exchanges.ports import ExchangeApiClientPort
from rotki2.types import Timestamp
from rotki2.utils.misc import ts_sec_to_ms


class OkxApiClient(ExchangeApiClientPort):
    """OKX API client adapter.
    
    Implements the ExchangeApiClientPort interface for OKX exchange.
    Handles authentication, rate limiting, and API communication.
    """
    
    MAX_RESULTS = 100
    
    def __init__(
        self,
        api_key: str,
        secret: str,
        passphrase: str,
    ) -> None:
        """Initialize OKX API client.
        
        Args:
            api_key: OKX API key
            secret: OKX API secret (base64 encoded)
            passphrase: OKX API passphrase
        """
        self.api_key = api_key
        self.secret = secret.encode('utf-8')
        self.passphrase = passphrase
        self.base_url = 'https://www.okx.com'
        
        # Initialize the generic client
        self.client = GenericApiClient(
            name='OKX',
            base_url=self.base_url,
            timeout=30,
        )
        
    async def __aenter__(self) -> 'OkxApiClient':
        """Async context manager entry."""
        await self.client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _generate_signature(
        self,
        timestamp: str,
        method: str,
        path: str,
        body: str = '',
    ) -> str:
        """Generate OKX API signature.
        
        OKX uses: timestamp + method + path + body
        signed with HMAC-SHA256 and base64 encoded.
        """
        prehash = timestamp + method.upper() + path + body
        signature = hmac.new(
            self.secret,
            prehash.encode('utf-8'),
            hashlib.sha256,
        )
        return base64.b64encode(signature.digest()).decode('utf-8')
    
    def _get_auth_headers(
        self,
        method: str,
        path: str,
        body: str = '',
    ) -> dict[str, str]:
        """Get authentication headers for OKX API."""
        # OKX requires ISO format timestamp with milliseconds
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        signature = self._generate_signature(timestamp, method, path, body)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json',
        }
    
    async def _api_query(
        self,
        endpoint: str,
        method: Literal['GET', 'POST'] = 'GET',
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated API query to OKX."""
        # Build path with query parameters
        path = endpoint
        if params:
            path += f'?{urlencode(params)}'
            
        # Get auth headers
        headers = self._get_auth_headers(method, path)
        
        # Make request
        response = await self.client.request(
            method=self.client.RequestMethod[method],
            path=path,
            headers=headers,
        )
        
        # OKX wraps responses in a standard format
        if isinstance(response, dict):
            if response.get('code') != '0':
                raise Exception(f"OKX API error: {response.get('msg', 'Unknown error')}")
            return response
        
        return {'data': response}
    
    async def get_balances(self) -> list[dict[str, Any]]:
        """Fetch current balances from trading and funding accounts."""
        balances = []
        
        # Get trading account balances
        trading_response = await self._api_query('/api/v5/account/balance')
        if trading_data := trading_response.get('data', []):
            for account in trading_data:
                for balance in account.get('details', []):
                    if balance:
                        balance['account_type'] = 'trading'
                        balances.append(balance)
        
        # Get funding account balances
        funding_response = await self._api_query('/api/v5/asset/balances')
        if funding_data := funding_response.get('data', []):
            for balance in funding_data:
                if balance:
                    balance['account_type'] = 'funding'
                    balances.append(balance)
                    
        return balances
    
    async def get_trades(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch trades within the given time range."""
        all_trades = []
        after = None
        
        params = {
            'instType': 'SPOT',
            'state': 'filled',
            'limit': str(self.MAX_RESULTS),
        }
        
        # OKX uses millisecond timestamps
        if start_ts:
            params['begin'] = str(ts_sec_to_ms(start_ts))
        if end_ts:
            params['end'] = str(ts_sec_to_ms(end_ts))
            
        while True:
            if after:
                params['after'] = str(after)
                
            response = await self._api_query(
                '/api/v5/trade/orders-history-archive',
                params=params,
            )
            
            trades = response.get('data', [])
            if not trades:
                break
                
            all_trades.extend(trades)
            
            # Check if there are more pages
            if len(trades) < self.MAX_RESULTS:
                break
                
            # Get the ID of the last trade for pagination
            after = trades[-1].get('ordId')
            if not after:
                break
                
        return all_trades
    
    async def get_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch deposits and withdrawals within the given time range."""
        deposits = []
        withdrawals = []
        
        # Fetch deposits
        after = None
        while True:
            params = {'limit': str(self.MAX_RESULTS)}
            if after:
                params['after'] = str(after)
                
            response = await self._api_query(
                '/api/v5/asset/deposit-history',
                params=params,
            )
            
            items = response.get('data', [])
            if not items:
                break
                
            # Filter by timestamp
            for item in items:
                # OKX returns timestamps in milliseconds
                ts_ms = int(item.get('ts', 0))
                ts = Timestamp(ts_ms // 1000)
                
                if start_ts <= ts <= end_ts:
                    deposits.append(item)
                elif ts < start_ts:
                    # Since results are ordered by time desc, we can stop
                    after = None
                    break
                    
            if not after:
                break
                
            if len(items) < self.MAX_RESULTS:
                break
                
            after = items[-1].get('depId')
            
        # Fetch withdrawals
        after = None
        while True:
            params = {'limit': str(self.MAX_RESULTS)}
            if after:
                params['after'] = str(after)
                
            response = await self._api_query(
                '/api/v5/asset/withdrawal-history',
                params=params,
            )
            
            items = response.get('data', [])
            if not items:
                break
                
            # Filter by timestamp
            for item in items:
                # OKX returns timestamps in milliseconds
                ts_ms = int(item.get('ts', 0))
                ts = Timestamp(ts_ms // 1000)
                
                if start_ts <= ts <= end_ts:
                    withdrawals.append(item)
                elif ts < start_ts:
                    # Since results are ordered by time desc, we can stop
                    after = None
                    break
                    
            if not after:
                break
                
            if len(items) < self.MAX_RESULTS:
                break
                
            after = items[-1].get('wdId')
            
        return deposits, withdrawals
    
    async def get_order_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch order history. For OKX, this is the same as trades."""
        return await self.get_trades(start_ts, end_ts, market)
    
    async def get_markets(self) -> list[dict[str, Any]]:
        """Fetch available trading markets/pairs."""
        response = await self._api_query('/api/v5/public/instruments', params={'instType': 'SPOT'})
        return response.get('data', [])