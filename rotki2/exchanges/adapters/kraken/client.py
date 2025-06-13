"""Kraken API client adapter implementation."""
import time
import urllib.parse
from typing import Any, Literal

from rotki2.exchanges.common.auth import HmacSigner, HashAlgorithm, Encoding
from rotki2.exchanges.common.client import GenericApiClient
from rotki2.exchanges.kraken import KrakenAccountType
from rotki2.exchanges.ports import ExchangeApiClientPort
from rotki2.types import Timestamp
from rotki2.utils.misc import ts_now_in_ms

KRAKEN_API_VERSION = '0'
KRAKEN_BASE_URL = 'https://api.kraken.com'


class KrakenApiClient(ExchangeApiClientPort):
    """Kraken API client adapter.
    
    Handles authentication, rate limiting, and API communication for Kraken.
    """
    
    def __init__(
        self,
        api_key: str,
        secret: str,
        account_type: KrakenAccountType = KrakenAccountType.STARTER,
    ) -> None:
        """Initialize Kraken API client.
        
        Args:
            api_key: Kraken API key
            secret: Kraken API secret (base64 encoded)
            account_type: Kraken account tier for rate limiting
        """
        self.api_key = api_key
        self.secret = secret
        self.account_type = account_type
        
        # Initialize HMAC signer for Kraken's specific requirements
        self.signer = HmacSigner(
            secret=secret,
            algorithm=HashAlgorithm.SHA512,
            encoding=Encoding.BASE64,
            decode_secret=True,  # Kraken secret is base64 encoded
        )
        
        # Set rate limits based on account type
        self._set_rate_limits()
        
        # Initialize generic client
        self.client = GenericApiClient(
            name='Kraken',
            base_url=KRAKEN_BASE_URL,
            timeout=30,
        )
        
        # Rate limiting state
        self.call_counter = 0
        self.last_counter_reduction = ts_now_in_ms()
        
    def _set_rate_limits(self) -> None:
        """Set rate limits based on account type."""
        if self.account_type == KrakenAccountType.STARTER:
            self.call_limit = 15
            self.reduction_every_secs = 60
        elif self.account_type == KrakenAccountType.INTERMEDIATE:
            self.call_limit = 20
            self.reduction_every_secs = 60
        else:  # Pro
            self.call_limit = 20
            self.reduction_every_secs = 1
            
    async def __aenter__(self) -> 'KrakenApiClient':
        """Async context manager entry."""
        await self.client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _generate_signature(self, urlpath: str, data: dict[str, Any], nonce: int) -> str:
        """Generate Kraken API signature.
        
        Kraken uses: SHA256(nonce + POST data) then HMAC-SHA512
        """
        import hashlib
        
        postdata = urllib.parse.urlencode(data)
        encoded = (str(nonce) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        # Use our HMAC signer with raw message
        return self.signer.sign(message)
    
    async def _api_query(
        self,
        method: str,
        req: dict[str, Any] | None = None,
        is_private: bool = True,
    ) -> dict[str, Any]:
        """Make an API query to Kraken."""
        if req is None:
            req = {}
            
        # Apply rate limiting
        current_time = ts_now_in_ms()
        secs_since_last = (current_time - self.last_counter_reduction) / 1000
        
        if secs_since_last > self.reduction_every_secs:
            self.call_counter = max(0, self.call_counter - 1)
            self.last_counter_reduction = current_time
            
        if self.call_counter >= self.call_limit:
            # Wait for rate limit reset
            import asyncio
            wait_time = self.reduction_every_secs * 2
            await asyncio.sleep(wait_time)
            self.call_counter = 0
            
        self.call_counter += 1
        
        # Build request
        if is_private:
            req['nonce'] = int(time.time() * 1000)
            urlpath = f'/{KRAKEN_API_VERSION}/private/{method}'
            headers = {
                'API-Key': self.api_key,
                'API-Sign': self._generate_signature(urlpath, req, req['nonce']),
            }
            
            response = await self.client.post(
                path=urlpath,
                data=req,
                headers=headers,
            )
        else:
            urlpath = f'/{KRAKEN_API_VERSION}/public/{method}'
            response = await self.client.get(
                path=urlpath,
                params=req,
            )
            
        # Kraken wraps responses
        if isinstance(response, dict):
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")
            return response.get('result', {})
            
        return response
    
    async def get_balances(self) -> list[dict[str, Any]]:
        """Fetch current balances."""
        result = await self._api_query('Balance')
        
        # Convert Kraken's balance format to our standard format
        balances = []
        for asset, balance in result.items():
            balances.append({
                'asset': asset,
                'balance': balance,
            })
            
        return balances
    
    async def get_trades(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch trades within the given time range."""
        req = {
            'start': str(start_ts),
            'end': str(end_ts),
        }
        
        if market:
            req['pair'] = market
            
        result = await self._api_query('TradesHistory', req)
        
        # Extract trades from result
        trades = []
        if 'trades' in result:
            for trade_id, trade_data in result['trades'].items():
                trade_data['id'] = trade_id
                trades.append(trade_data)
                
        return trades
    
    async def get_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch deposits and withdrawals."""
        # Kraken uses ledgers for both deposits and withdrawals
        req = {
            'start': str(start_ts),
            'end': str(end_ts),
        }
        
        result = await self._api_query('Ledgers', req)
        
        deposits = []
        withdrawals = []
        
        if 'ledger' in result:
            for ledger_id, ledger_data in result['ledger'].items():
                ledger_data['id'] = ledger_id
                
                # Determine if deposit or withdrawal based on type
                if ledger_data.get('type') == 'deposit':
                    deposits.append(ledger_data)
                elif ledger_data.get('type') == 'withdrawal':
                    withdrawals.append(ledger_data)
                    
        return deposits, withdrawals
    
    async def get_order_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch order history."""
        req = {
            'start': str(start_ts),
            'end': str(end_ts),
        }
        
        if market:
            req['pair'] = market
            
        result = await self._api_query('ClosedOrders', req)
        
        orders = []
        if 'closed' in result:
            for order_id, order_data in result['closed'].items():
                order_data['id'] = order_id
                orders.append(order_data)
                
        return orders
    
    async def get_markets(self) -> list[dict[str, Any]]:
        """Fetch available trading pairs."""
        result = await self._api_query('AssetPairs', is_private=False)
        
        markets = []
        for pair_name, pair_data in result.items():
            pair_data['symbol'] = pair_name
            markets.append(pair_data)
            
        return markets