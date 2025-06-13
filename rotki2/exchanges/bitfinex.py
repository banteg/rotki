"""Bitfinex exchange implementation"""
import hashlib
import hmac
import json
import time
from typing import TYPE_CHECKING, Any

import anyio

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_bitfinex
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import RemoteError
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

BITFINEX_BASE_URL = 'https://api.bitfinex.com'
BITFINEX_API_VERSION = 'v2'


class Bitfinex(ExchangeInterface):
    """Bitfinex exchange implementation"""
    
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
            location=Location.BITFINEX,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        # Bitfinex rate limits: 90 requests per minute for authenticated endpoints
        self.rate_limit_calls = 90
        self.rate_limit_period = 60
    
    def _generate_nonce(self) -> str:
        """Generate nonce for API requests"""
        return str(int(time.time() * 1000000))
    
    def _generate_signature(self, path: str, nonce: str, body: str) -> str:
        """Generate signature for authenticated requests"""
        signature_payload = f'/api/{BITFINEX_API_VERSION}{path}{nonce}{body}'
        
        return hmac.new(
            self.secret.encode('utf-8'),
            signature_payload.encode('utf-8'),
            hashlib.sha384,
        ).hexdigest()
    
    async def _api_query(
        self,
        endpoint: str,
        method: str = 'POST',
        data: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        """Query Bitfinex API"""
        # Apply rate limiting
        await self._apply_rate_limit()
        
        path = f'/auth/r/{endpoint}' if authenticated else f'/{endpoint}'
        url = f'{BITFINEX_BASE_URL}/{BITFINEX_API_VERSION}{path}'
        
        headers = {}
        
        if authenticated:
            nonce = self._generate_nonce()
            body = json.dumps(data) if data else '{}'
            
            headers = {
                'bfx-nonce': nonce,
                'bfx-apikey': self.api_key,
                'bfx-signature': self._generate_signature(path, nonce, body),
                'content-type': 'application/json',
            }
        
        # Make request
        try:
            if method == 'GET':
                response = await self.http_client.get(url, headers=headers)
            elif method == 'POST':
                response = await self.http_client.post(
                    url,
                    json=data if data else {},
                    headers=headers,
                )
            else:
                raise ValueError(f'Unsupported HTTP method: {method}')
            
            if response.status_code != 200:
                raise RemoteError(
                    f'Bitfinex API request failed with status {response.status_code}: '
                    f'{response.text}'
                )
            
            result = response.json()
            
            # Check for errors
            if isinstance(result, list) and len(result) > 0 and result[0] == 'error':
                raise RemoteError(f'Bitfinex API error: {result}')
            
            return result
            
        except Exception as e:
            raise RemoteError(f'Bitfinex API request failed: {e}') from e
    
    async def validate_api_key(self) -> tuple[bool, str]:
        """Validate API credentials"""
        try:
            # Query account info to validate
            await self._api_query('account_info')
            return True, ''
        except RemoteError as e:
            error_str = str(e)
            if 'apikey' in error_str.lower() or 'unauthorized' in error_str.lower():
                return False, 'Invalid API credentials'
            else:
                return False, f'API validation failed: {error_str}'
    
    async def query_balances(self, **kwargs: Any) -> dict[Asset, Balance]:
        """Query account balances"""
        # Query wallet balances
        response = await self._api_query('wallets')
        
        balances = {}
        
        # Response is a list of wallet entries
        for entry in response:
            try:
                # Entry format: [wallet_type, currency, balance, unsettled_interest, available]
                if len(entry) < 5:
                    continue
                
                wallet_type = entry[0]
                currency = entry[1]
                balance = FVal(entry[2])
                available = FVal(entry[4])
                
                # Skip if no balance
                if balance <= ZERO:
                    continue
                
                # Convert currency to asset
                asset = asset_from_bitfinex(currency)
                if not asset:
                    continue
                
                # Aggregate balances across wallet types
                if asset in balances:
                    current = balances[asset]
                    balances[asset] = Balance(
                        amount=current.amount + balance,
                        usd_value=current.usd_value + balance,  # Simplified
                    )
                else:
                    balances[asset] = Balance(
                        amount=balance,
                        usd_value=balance,  # Simplified USD calculation
                    )
                
            except (ValueError, IndexError) as e:
                logger.warning(f'Failed to process Bitfinex balance entry: {e}')
                continue
        
        return balances
    
    async def query_online_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history"""
        trades = []
        
        # Convert timestamps to milliseconds
        start_ms = start_ts * 1000
        end_ms = end_ts * 1000
        
        # Query trades with pagination
        limit = 1000  # Max allowed by Bitfinex
        last_id = None
        
        while True:
            params = {
                'start': start_ms,
                'end': end_ms,
                'limit': limit,
            }
            
            if last_id:
                params['until'] = last_id
            
            response = await self._api_query('trades/hist', data=params)
            
            if not response or not isinstance(response, list):
                break
            
            for trade_data in response:
                try:
                    # Trade format: [ID, PAIR, MTS_CREATE, ORDER_ID, EXEC_AMOUNT, EXEC_PRICE, ORDER_TYPE, ORDER_PRICE, MAKER, FEE, FEE_CURRENCY]
                    if len(trade_data) < 11:
                        continue
                    
                    trade_id = trade_data[0]
                    pair = trade_data[1]
                    timestamp = trade_data[2] // 1000  # Convert from ms
                    amount = FVal(str(trade_data[4]))
                    price = FVal(str(trade_data[5]))
                    fee = abs(FVal(str(trade_data[9])))
                    fee_currency = trade_data[10]
                    
                    # Parse pair (format: tBTCUSD)
                    if not pair.startswith('t'):
                        continue
                    
                    pair = pair[1:]  # Remove 't' prefix
                    
                    # Simple pair parsing - would need proper mapping
                    if len(pair) == 6:
                        base_str = pair[:3]
                        quote_str = pair[3:]
                    else:
                        logger.warning(f'Cannot parse Bitfinex pair: {pair}')
                        continue
                    
                    base_asset = asset_from_bitfinex(base_str)
                    quote_asset = asset_from_bitfinex(quote_str)
                    
                    if not base_asset or not quote_asset:
                        continue
                    
                    # Determine trade type from amount sign
                    trade_type = TradeType.BUY if amount > 0 else TradeType.SELL
                    amount = abs(amount)
                    
                    # Convert fee currency
                    fee_asset = asset_from_bitfinex(fee_currency) if fee_currency else quote_asset
                    
                    trade = Trade(
                        timestamp=timestamp,
                        location=Location.BITFINEX,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        trade_type=trade_type,
                        amount=amount,
                        rate=price,
                        fee=fee,
                        fee_currency=fee_asset,
                        link=str(trade_id),
                    )
                    trades.append(trade)
                    
                    # Track last ID for pagination
                    if last_id is None or trade_id < last_id:
                        last_id = trade_id
                    
                except Exception as e:
                    logger.warning(f'Failed to parse Bitfinex trade: {e}')
                    continue
            
            # If we got less than limit, we're done
            if len(response) < limit:
                break
        
        return trades
    
    async def query_online_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals"""
        movements = []
        
        # Convert timestamps to milliseconds
        start_ms = start_ts * 1000
        end_ms = end_ts * 1000
        
        # Query movements
        params = {
            'start': start_ms,
            'end': end_ms,
            'limit': 1000,
        }
        
        response = await self._api_query('movements/hist', data=params)
        
        for movement_data in response:
            try:
                # Format: [ID, CURRENCY, CURRENCY_NAME, MTS_STARTED, MTS_UPDATED, STATUS, AMOUNT, FEES, DESTINATION_ADDRESS, TRANSACTION_ID]
                if len(movement_data) < 10:
                    continue
                
                movement_id = movement_data[0]
                currency = movement_data[1]
                timestamp = movement_data[3] // 1000  # Convert from ms
                status = movement_data[5]
                amount = FVal(str(movement_data[6]))
                fees = abs(FVal(str(movement_data[7])))
                address = movement_data[8]
                tx_id = movement_data[9]
                
                # Skip non-completed movements
                if status != 'COMPLETED':
                    continue
                
                # Convert currency
                asset = asset_from_bitfinex(currency)
                if not asset:
                    continue
                
                # Determine category from amount sign
                category = AssetMovementCategory.DEPOSIT if amount > 0 else AssetMovementCategory.WITHDRAWAL
                amount = abs(amount)
                
                movement = AssetMovement(
                    location=Location.BITFINEX,
                    category=category,
                    timestamp=timestamp,
                    address=address,
                    transaction_id=tx_id,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=fees,
                    link=str(movement_id),
                )
                movements.append(movement)
                
            except Exception as e:
                logger.warning(f'Failed to parse Bitfinex movement: {e}')
                continue
        
        return movements