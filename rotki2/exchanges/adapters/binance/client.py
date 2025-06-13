"""Binance API client adapter implementation."""
import time
from typing import Any, Literal
from urllib.parse import urlencode

from rotki2.exchanges.common.auth import HmacSigner, HashAlgorithm, Encoding
from rotki2.exchanges.common.client import GenericApiClient
from rotki2.exchanges.ports import ExchangeApiClientPort
from rotki2.types import Timestamp
from rotki2.utils.misc import ts_sec_to_ms

BINANCE_BASE_URL = 'https://api.binance.com'
BINANCEUS_BASE_URL = 'https://api.binance.us'


class BinanceApiClient(ExchangeApiClientPort):
    """Binance API client adapter.
    
    Handles authentication and API communication for Binance/BinanceUS.
    """
    
    def __init__(
        self,
        api_key: str,
        secret: str,
        uri: str = BINANCE_BASE_URL,
    ) -> None:
        """Initialize Binance API client.
        
        Args:
            api_key: Binance API key
            secret: Binance API secret
            uri: Base URI (different for Binance US)
        """
        self.api_key = api_key
        self.secret = secret
        self.base_url = uri
        
        # Initialize HMAC signer for Binance
        self.signer = HmacSigner(
            secret=secret,
            algorithm=HashAlgorithm.SHA256,
            encoding=Encoding.HEX,
            decode_secret=False,  # Binance secret is plain text
        )
        
        # Initialize generic client
        self.client = GenericApiClient(
            name='Binance',
            base_url=self.base_url,
            timeout=30,
        )
        
    async def __aenter__(self) -> 'BinanceApiClient':
        """Async context manager entry."""
        await self.client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _sign_request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Sign request parameters for Binance."""
        # Add timestamp
        params['timestamp'] = str(int(time.time() * 1000))
        
        # Create query string and sign it
        query_string = urlencode(sorted(params.items()))
        signature = self.signer.sign(query_string)
        
        # Add signature to params
        params['signature'] = signature
        return params
    
    async def _api_query(
        self,
        endpoint: str,
        method: Literal['GET', 'POST'] = 'GET',
        params: dict[str, Any] | None = None,
        signed: bool = True,
    ) -> Any:
        """Make an API query to Binance."""
        if params is None:
            params = {}
            
        headers = {}
        if signed:
            headers['X-MBX-APIKEY'] = self.api_key
            params = self._sign_request(params)
            
        if method == 'GET':
            response = await self.client.get(
                path=endpoint,
                params=params,
                headers=headers,
            )
        else:
            response = await self.client.post(
                path=endpoint,
                data=params,
                headers=headers,
            )
            
        return response
    
    async def get_balances(self) -> list[dict[str, Any]]:
        """Fetch current balances."""
        response = await self._api_query('/api/v3/account')
        
        # Extract balances from account info
        balances = []
        for balance in response.get('balances', []):
            # Only include non-zero balances
            free = float(balance.get('free', 0))
            locked = float(balance.get('locked', 0))
            
            if free > 0 or locked > 0:
                balances.append({
                    'asset': balance['asset'],
                    'free': balance['free'],
                    'locked': balance['locked'],
                })
                
        return balances
    
    async def get_trades(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch trades within the given time range."""
        all_trades = []
        
        if market:
            # Query specific market
            symbols = [market]
        else:
            # Get all traded symbols from account
            account = await self._api_query('/api/v3/account')
            traded_assets = set()
            
            for balance in account.get('balances', []):
                if float(balance.get('free', 0)) > 0 or float(balance.get('locked', 0)) > 0:
                    traded_assets.add(balance['asset'])
                    
            # Generate possible trading pairs
            # This is a simplified approach - in production, you'd want to
            # query the exchange info endpoint for actual pairs
            quote_assets = ['USDT', 'BTC', 'ETH', 'BNB', 'BUSD']
            symbols = []
            
            for asset in traded_assets:
                if asset not in quote_assets:
                    for quote in quote_assets:
                        symbols.append(f'{asset}{quote}')
                        
        # Query trades for each symbol
        for symbol in symbols:
            try:
                params = {
                    'symbol': symbol,
                    'limit': 1000,  # Max allowed
                }
                
                if start_ts:
                    params['startTime'] = ts_sec_to_ms(start_ts)
                if end_ts:
                    params['endTime'] = ts_sec_to_ms(end_ts)
                    
                trades = await self._api_query('/api/v3/myTrades', params=params)
                
                # Add symbol to each trade for easier processing
                for trade in trades:
                    trade['symbol'] = symbol
                    
                all_trades.extend(trades)
                
            except Exception:
                # Symbol might not exist or have no trades
                continue
                
        return all_trades
    
    async def get_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch deposits and withdrawals."""
        deposits = []
        withdrawals = []
        
        # Fetch deposits
        params = {}
        if start_ts:
            params['startTime'] = ts_sec_to_ms(start_ts)
        if end_ts:
            params['endTime'] = ts_sec_to_ms(end_ts)
            
        try:
            deposit_history = await self._api_query(
                '/sapi/v1/capital/deposit/hisrec',
                params=params,
            )
            deposits = deposit_history if isinstance(deposit_history, list) else []
        except Exception as e:
            # Endpoint might not be available for all accounts
            pass
            
        # Fetch withdrawals
        try:
            withdraw_history = await self._api_query(
                '/sapi/v1/capital/withdraw/history',
                params=params,
            )
            withdrawals = withdraw_history if isinstance(withdraw_history, list) else []
        except Exception:
            # Endpoint might not be available for all accounts
            pass
            
        return deposits, withdrawals
    
    async def get_order_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch order history."""
        # For Binance, we use the trades endpoint as it provides filled orders
        return await self.get_trades(start_ts, end_ts, market)
    
    async def get_markets(self) -> list[dict[str, Any]]:
        """Fetch available trading pairs."""
        response = await self._api_query(
            '/api/v3/exchangeInfo',
            signed=False,
        )
        
        markets = []
        for symbol_info in response.get('symbols', []):
            if symbol_info.get('status') == 'TRADING':
                markets.append({
                    'symbol': symbol_info['symbol'],
                    'baseAsset': symbol_info['baseAsset'],
                    'quoteAsset': symbol_info['quoteAsset'],
                    'status': symbol_info['status'],
                })
                
        return markets