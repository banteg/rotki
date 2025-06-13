"""Coinbase exchange implementation"""
import base64
import hashlib
import hmac
import time
from typing import TYPE_CHECKING, Any

import anyio

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    AssetMovementCategory,
    Trade,
    TradeType,
)
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    Location,
    Timestamp,
)
from rotki2.exchanges.base import ExchangeInterface

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = RotkehlchenLogsAdapter(__name__)

COINBASE_BASE_URL = 'https://api.coinbase.com'
COINBASE_API_VERSION = '2023-11-01'


class Coinbase(ExchangeInterface):
    """Coinbase exchange implementation
    
    Uses the new Advanced Trade API which replaced Coinbase Pro.
    """
    
    def __init__(
        self,
        name: str,
        api_key: ApiKey,
        secret: ApiSecret,
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            name=name,
            location=Location.COINBASE,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        # Coinbase rate limits: 30 requests per second
        self.rate_limit_calls = 30
        self.rate_limit_period = 1
    
    def _generate_signature(
        self,
        method: str,
        path: str,
        body: str = '',
        timestamp: str | None = None,
    ) -> tuple[str, str]:
        """Generate signature for Coinbase API requests"""
        if timestamp is None:
            timestamp = str(int(time.time()))
        
        message = f'{timestamp}{method}{path}{body}'
        signature = hmac.new(
            self.secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        
        return signature, timestamp
    
    async def _api_query(
        self,
        endpoint: str,
        method: str = 'GET',
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query Coinbase API"""
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Prepare request
        path = f'/api/v3/{endpoint}'
        url = f'{COINBASE_BASE_URL}{path}'
        
        body = ''
        if data and method != 'GET':
            import json
            body = json.dumps(data)
        
        # Generate signature
        signature, timestamp = self._generate_signature(method, path, body)
        
        headers = {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-VERSION': COINBASE_API_VERSION,
            'Content-Type': 'application/json',
        }
        
        # Make request
        try:
            if method == 'GET':
                response = await self.http_client.get(url, headers=headers)
            elif method == 'POST':
                response = await self.http_client.post(url, json=data, headers=headers)
            else:
                raise ValueError(f'Unsupported HTTP method: {method}')
            
            if response.status_code != 200:
                raise RemoteError(
                    f'Coinbase API request failed with status {response.status_code}: '
                    f'{response.text}'
                )
            
            return response.json()
            
        except Exception as e:
            raise RemoteError(f'Coinbase API request failed: {e}') from e
    
    async def validate_api_key(self) -> tuple[bool, str]:
        """Validate API credentials"""
        try:
            await self._api_query('brokerage/accounts')
            return True, ''
        except RemoteError as e:
            error_str = str(e)
            if 'authentication' in error_str.lower():
                return False, 'Invalid API credentials'
            else:
                return False, f'API validation failed: {error_str}'
    
    async def query_balances(self, **kwargs: Any) -> dict[Asset, Balance]:
        """Query account balances"""
        response = await self._api_query('brokerage/accounts')
        
        balances = {}
        for account_data in response.get('accounts', []):
            try:
                # Skip non-crypto accounts
                if account_data.get('type') != 'ACCOUNT_TYPE_CRYPTO':
                    continue
                
                currency = account_data.get('currency')
                if not currency:
                    continue
                
                asset = asset_from_coinbase(currency)
                if not asset:
                    continue
                
                # Get balance details
                available_balance = FVal(account_data.get('available_balance', {}).get('value', '0'))
                hold = FVal(account_data.get('hold', {}).get('value', '0'))
                
                amount = available_balance + hold
                if amount <= ZERO:
                    continue
                
                # Simplified USD value calculation
                usd_value = amount  # Would calculate actual USD value
                
                balances[asset] = Balance(amount=amount, usd_value=usd_value)
                
            except (ValueError, KeyError) as e:
                logger.warning(f'Failed to process Coinbase balance: {e}')
                continue
        
        return balances
    
    async def query_online_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history"""
        trades = []
        
        # Query fills (executed trades)
        params = {
            'start_sequence_timestamp': start_ts,
            'end_sequence_timestamp': end_ts,
            'limit': 100,
        }
        
        cursor = None
        while True:
            if cursor:
                params['cursor'] = cursor
            
            response = await self._api_query('brokerage/orders/historical/fills', data=params)
            
            for fill in response.get('fills', []):
                try:
                    # Parse trading pair
                    product_id = fill['product_id']
                    base_currency, quote_currency = product_id.split('-')
                    
                    base_asset = asset_from_coinbase(base_currency)
                    quote_asset = asset_from_coinbase(quote_currency)
                    
                    if not base_asset or not quote_asset:
                        continue
                    
                    # Determine trade type
                    side = fill['side']
                    trade_type = TradeType.BUY if side == 'BUY' else TradeType.SELL
                    
                    # Parse amounts
                    size = deserialize_asset_amount(fill['size'])
                    price = deserialize_price(fill['price'])
                    fee = deserialize_fee(fill['commission'])
                    
                    # Create trade
                    trade = Trade(
                        timestamp=deserialize_timestamp(fill['trade_time']),
                        location=Location.COINBASE,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        trade_type=trade_type,
                        amount=size,
                        rate=price,
                        fee=fee,
                        fee_currency=quote_asset,  # Coinbase charges fees in quote currency
                        link=fill['trade_id'],
                    )
                    trades.append(trade)
                    
                except Exception as e:
                    logger.warning(f'Failed to parse Coinbase trade: {e}')
                    continue
            
            # Check if there are more pages
            cursor = response.get('cursor')
            if not cursor:
                break
        
        return trades
    
    async def query_online_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals"""
        movements = []
        
        # Note: Coinbase's new API doesn't have a direct endpoint for historical transfers
        # This would need to be implemented using transaction history or webhooks
        # For now, return empty list as a placeholder
        
        logger.warning(
            'Coinbase deposits/withdrawals query not fully implemented in new API. '
            'Consider using transaction export.'
        )
        
        return movements