"""Coinbase API client adapter implementation."""
import base64
import time
from typing import Any, Literal

from rotki2.exchanges.common.auth import HmacSigner, HashAlgorithm, Encoding
from rotki2.exchanges.common.client import GenericApiClient
from rotki2.exchanges.ports import ExchangeApiClientPort
from rotki2.types import Timestamp

COINBASE_BASE_URL = 'https://api.exchange.coinbase.com'


class CoinbaseApiClient(ExchangeApiClientPort):
    """Coinbase API client adapter.
    
    Handles authentication and API communication for Coinbase Pro/Exchange.
    """
    
    def __init__(
        self,
        api_key: str,
        secret: str,
        passphrase: str | None = None,
    ) -> None:
        """Initialize Coinbase API client.
        
        Args:
            api_key: Coinbase API key
            secret: Coinbase API secret (base64 encoded)
            passphrase: Coinbase API passphrase (not used in newer API)
        """
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        
        # Initialize HMAC signer for Coinbase
        self.signer = HmacSigner(
            secret=secret,
            algorithm=HashAlgorithm.SHA256,
            encoding=Encoding.BASE64,
            decode_secret=True,  # Coinbase secret is base64 encoded
        )
        
        # Initialize generic client
        self.client = GenericApiClient(
            name='Coinbase',
            base_url=COINBASE_BASE_URL,
            timeout=30,
        )
        
    async def __aenter__(self) -> 'CoinbaseApiClient':
        """Async context manager entry."""
        await self.client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _get_auth_headers(
        self,
        method: str,
        path: str,
        body: str = '',
    ) -> dict[str, str]:
        """Get authentication headers for Coinbase API.
        
        Coinbase uses: timestamp + method + path + body
        """
        timestamp = str(time.time())
        message = timestamp + method.upper() + path + body
        signature = self.signer.sign(message)
        
        headers = {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
        }
        
        # Add passphrase if provided (older API)
        if self.passphrase:
            headers['CB-ACCESS-PASSPHRASE'] = self.passphrase
            
        return headers
    
    async def _api_query(
        self,
        endpoint: str,
        method: Literal['GET', 'POST'] = 'GET',
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Make an authenticated API query to Coinbase."""
        # Get auth headers
        headers = self._get_auth_headers(
            method,
            endpoint,
            '' if not data else str(data),
        )
        
        # Make request
        if method == 'GET':
            response = await self.client.get(
                path=endpoint,
                params=params,
                headers=headers,
            )
        else:
            response = await self.client.post(
                path=endpoint,
                json=data,
                headers=headers,
            )
            
        return response
    
    async def get_balances(self) -> list[dict[str, Any]]:
        """Fetch current balances."""
        accounts = await self._api_query('/accounts')
        
        # Convert to standard format
        balances = []
        for account in accounts:
            balance = float(account.get('balance', 0))
            if balance > 0:
                balances.append({
                    'currency': account['currency'],
                    'balance': account['balance'],
                    'available': account['available'],
                    'hold': account['hold'],
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
        
        # Get list of products to query
        if market:
            products = [market]
        else:
            # Get all traded products
            fills = await self._api_query('/fills')
            products = list(set(fill['product_id'] for fill in fills[:100]))
            
        # Query fills for each product
        for product_id in products:
            params = {
                'product_id': product_id,
            }
            
            # Coinbase doesn't support time filtering in fills endpoint
            # We'll filter manually after fetching
            try:
                fills = await self._api_query('/fills', params=params)
                
                # Filter by time range
                for fill in fills:
                    # Parse ISO timestamp
                    from datetime import datetime
                    try:
                        created_at = fill.get('created_at', '')
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        fill_ts = Timestamp(int(dt.timestamp()))
                        
                        if start_ts <= fill_ts <= end_ts:
                            all_trades.append(fill)
                    except Exception:
                        continue
                        
            except Exception:
                # Product might not have any fills
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
        
        # Get all accounts
        accounts = await self._api_query('/accounts')
        
        for account in accounts:
            account_id = account['id']
            
            # Get transfers for this account
            try:
                transfers = await self._api_query(f'/accounts/{account_id}/transfers')
                
                for transfer in transfers:
                    # Parse timestamp
                    from datetime import datetime
                    try:
                        completed_at = transfer.get('completed_at', '')
                        if not completed_at:
                            continue
                            
                        dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                        transfer_ts = Timestamp(int(dt.timestamp()))
                        
                        if not (start_ts <= transfer_ts <= end_ts):
                            continue
                            
                        # Add currency info
                        transfer['currency'] = account['currency']
                        
                        # Determine type
                        if transfer.get('type') == 'deposit':
                            deposits.append(transfer)
                        elif transfer.get('type') == 'withdraw':
                            withdrawals.append(transfer)
                            
                    except Exception:
                        continue
                        
            except Exception:
                # Account might not have transfers
                continue
                
        return deposits, withdrawals
    
    async def get_order_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch order history."""
        params = {
            'status': 'done',  # Only completed orders
        }
        
        if market:
            params['product_id'] = market
            
        orders = await self._api_query('/orders', params=params)
        
        # Filter by time range
        filtered_orders = []
        for order in orders:
            from datetime import datetime
            try:
                done_at = order.get('done_at', '')
                if not done_at:
                    continue
                    
                dt = datetime.fromisoformat(done_at.replace('Z', '+00:00'))
                order_ts = Timestamp(int(dt.timestamp()))
                
                if start_ts <= order_ts <= end_ts:
                    filtered_orders.append(order)
            except Exception:
                continue
                
        return filtered_orders
    
    async def get_markets(self) -> list[dict[str, Any]]:
        """Fetch available trading pairs."""
        products = await self._api_query('/products')
        
        markets = []
        for product in products:
            if product.get('status') == 'online':
                markets.append({
                    'id': product['id'],
                    'base_currency': product['base_currency'],
                    'quote_currency': product['quote_currency'],
                    'status': product['status'],
                })
                
        return markets