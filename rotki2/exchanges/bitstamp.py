"""Bitstamp exchange implementation"""
import hashlib
import hmac
import time
import uuid
from typing import TYPE_CHECKING, Any, NamedTuple

import anyio

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.converters import asset_from_bitstamp
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
    deserialize_timestamp_from_bitstamp_date,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    Location,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now_in_ms, ts_sec_to_ms
from rotki2.exchanges.base import ExchangeInterface

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = RotkehlchenLogsAdapter(__name__)

# API error codes
API_ERR_AUTH_NONCE_CODE = 'API0017'
API_KEY_ERROR_CODE_ACTION = {
    'API0001': 'Check your API key value.',
    'API0002': 'The IP address has no permission to use this API key.',
    'API0003': (
        'Provided Bitstamp API key needs to have "Account balance" and "User transactions" '
        'permission activated. Please log into your Bitstamp account and create a key with '
        'the required permissions.'
    ),
    API_ERR_AUTH_NONCE_CODE: 'Bitstamp nonce too low error. Is the local system clock in synced?',
    'API0006': 'Contact Bitstamp support to unfreeze your account',
    'API0008': "Can't find a customer with selected API key.",
    'API0011': 'Check that your API key string is correct.',
}

# API constants
API_MAX_LIMIT = 1000
USER_TRANSACTION_SORTING_MODE = 'asc'
USER_TRANSACTION_MIN_SINCE_ID = 1
USER_TRANSACTION_TRADE_TYPE = {2}
USER_TRANSACTION_ASSET_MOVEMENT_TYPE = {0, 1}


class TradePairData(NamedTuple):
    pair: str
    base_asset_symbol: str
    quote_asset_symbol: str
    base_asset: AssetWithOracles
    quote_asset: AssetWithOracles


class Bitstamp(ExchangeInterface):
    """Bitstamp exchange implementation
    
    API docs: https://www.bitstamp.net/api/
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
            location=Location.BITSTAMP,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = 'https://www.bitstamp.net/api'
        
        # Bitstamp rate limits: 8000 requests per 10 minutes (13.33 per second)
        self.rate_limit_calls = 133
        self.rate_limit_period = 10
    
    def _generate_signature(
        self,
        method: str,
        path: str,
        query: str = '',
        content_type: str = '',
        body: str = '',
        nonce: str | None = None,
        timestamp: str | None = None,
    ) -> tuple[str, str, str]:
        """Generate signature for Bitstamp API v2"""
        if nonce is None:
            nonce = str(uuid.uuid4())
        if timestamp is None:
            timestamp = str(ts_now_in_ms())
        
        # Construct the message to sign
        message = f'BITSTAMP {self.api_key}{method}{self.base_uri}{path}{query}{content_type}{nonce}{timestamp}v2{body}'
        
        signature = hmac.new(
            self.secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        
        return signature, nonce, timestamp
    
    async def _api_query(
        self,
        endpoint: str,
        method: str = 'POST',
        data: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        """Query Bitstamp API"""
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Construct URL
        api_version = 'v2' if authenticated else 'v2'
        path = f'/{api_version}/{endpoint}/'
        url = f'{self.base_uri}{path}'
        
        headers = {}
        
        if authenticated:
            # Prepare request data
            if method == 'POST' and data:
                body = '&'.join([f'{k}={v}' for k, v in data.items()])
                content_type = 'application/x-www-form-urlencoded'
            else:
                body = ''
                content_type = ''
            
            # Generate authentication headers
            signature, nonce, timestamp = self._generate_signature(
                method=method,
                path=path,
                content_type=content_type,
                body=body,
            )
            
            headers = {
                'X-Auth': f'BITSTAMP {self.api_key}',
                'X-Auth-Signature': signature,
                'X-Auth-Nonce': nonce,
                'X-Auth-Timestamp': timestamp,
                'X-Auth-Version': 'v2',
            }
            
            if content_type:
                headers['Content-Type'] = content_type
        
        # Make request
        try:
            if method == 'GET':
                response = await self.http_client.get(url, params=data, headers=headers)
            elif method == 'POST':
                if authenticated and data:
                    response = await self.http_client.post(url, data=data, headers=headers)
                else:
                    response = await self.http_client.post(url, json=data, headers=headers)
            else:
                raise ValueError(f'Unsupported HTTP method: {method}')
            
            if response.status_code != 200:
                raise RemoteError(
                    f'Bitstamp API request failed with status {response.status_code}: '
                    f'{response.text}'
                )
            
            result = response.json()
            
            # Check for API errors
            if isinstance(result, dict) and 'status' in result and result['status'] == 'error':
                error_code = result.get('code', '')
                error_msg = API_KEY_ERROR_CODE_ACTION.get(error_code, result.get('reason', 'Unknown error'))
                raise RemoteError(f'Bitstamp API error {error_code}: {error_msg}')
            
            return result
            
        except Exception as e:
            raise RemoteError(f'Bitstamp API request failed: {e}') from e
    
    async def validate_api_key(self) -> tuple[bool, str]:
        """Validate API credentials"""
        try:
            await self._api_query('balance')
            return True, ''
        except RemoteError as e:
            error_str = str(e)
            for code, msg in API_KEY_ERROR_CODE_ACTION.items():
                if code in error_str:
                    return False, msg
            return False, f'API validation failed: {error_str}'
    
    async def query_balances(self, **kwargs: Any) -> dict[Asset, Balance]:
        """Query account balances"""
        response = await self._api_query('balance')
        
        balances = {}
        
        # Bitstamp returns balances as key-value pairs
        # Keys are like 'btc_available', 'btc_balance', 'btc_reserved'
        processed_assets = set()
        
        for key, value in response.items():
            if '_balance' not in key:
                continue
            
            # Extract currency from key (e.g., 'btc' from 'btc_balance')
            currency = key.replace('_balance', '')
            
            if currency in processed_assets:
                continue
            
            processed_assets.add(currency)
            
            try:
                # Get total balance
                balance = FVal(value)
                
                if balance <= ZERO:
                    continue
                
                # Convert currency to asset
                asset = asset_from_bitstamp(currency.upper())
                if not asset:
                    continue
                
                # Simplified USD value calculation
                usd_value = balance  # Would calculate actual USD value
                
                balances[asset] = Balance(amount=balance, usd_value=usd_value)
                
            except (ValueError, KeyError) as e:
                logger.warning(f'Failed to process Bitstamp balance for {currency}: {e}')
                continue
        
        return balances
    
    async def query_online_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history"""
        trades = []
        
        # Query user transactions
        params = {
            'limit': API_MAX_LIMIT,
            'sort': USER_TRANSACTION_SORTING_MODE,
            'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        }
        
        while True:
            response = await self._api_query('user_transactions', data=params)
            
            if not response:
                break
            
            for transaction in response:
                try:
                    # Filter for trade transactions
                    if transaction.get('type') not in USER_TRANSACTION_TRADE_TYPE:
                        continue
                    
                    # Parse timestamp
                    timestamp = deserialize_timestamp_from_bitstamp_date(transaction['datetime'])
                    
                    # Skip if outside time range
                    if timestamp < start_ts or timestamp > end_ts:
                        continue
                    
                    # Parse trade details
                    # Find base and quote assets from transaction keys
                    base_asset = None
                    quote_asset = None
                    amount = None
                    cost = None
                    fee = ZERO
                    fee_currency = None
                    
                    # Look for currency pairs in transaction
                    for key in transaction:
                        if key.endswith('_btc') or key.endswith('_usd') or key.endswith('_eur'):
                            # This is an amount in a trading pair
                            parts = key.split('_')
                            if len(parts) == 2:
                                asset_str = parts[0].upper()
                                currency_str = parts[1].upper()
                                
                                value = FVal(transaction[key])
                                if value > ZERO:
                                    # This is what we received
                                    base_asset = asset_from_bitstamp(asset_str)
                                    amount = value
                                elif value < ZERO:
                                    # This is what we spent
                                    quote_asset = asset_from_bitstamp(currency_str)
                                    cost = abs(value)
                    
                    if not all([base_asset, quote_asset, amount, cost]):
                        logger.warning(f'Could not parse Bitstamp trade {transaction}')
                        continue
                    
                    # Parse fee
                    if 'fee' in transaction:
                        fee = deserialize_fee(transaction['fee'])
                        # Fee is usually in quote currency
                        fee_currency = quote_asset
                    
                    # Determine trade type based on what we received/spent
                    # This is simplified - actual logic would be more complex
                    trade_type = TradeType.BUY
                    
                    # Calculate rate
                    rate = cost / amount if amount > ZERO else ZERO
                    
                    trade = Trade(
                        timestamp=timestamp,
                        location=Location.BITSTAMP,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        trade_type=trade_type,
                        amount=amount,
                        rate=rate,
                        fee=fee,
                        fee_currency=fee_currency,
                        link=str(transaction['id']),
                    )
                    trades.append(trade)
                    
                except Exception as e:
                    logger.warning(f'Failed to parse Bitstamp trade: {e}')
                    continue
            
            # Check if we need to query more
            if len(response) < API_MAX_LIMIT:
                break
            
            # Update since_id for next query
            last_id = response[-1]['id']
            params['since_id'] = last_id + 1
        
        return trades
    
    async def query_online_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals"""
        movements = []
        
        # Query user transactions for deposits/withdrawals
        params = {
            'limit': API_MAX_LIMIT,
            'sort': USER_TRANSACTION_SORTING_MODE,
            'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        }
        
        while True:
            response = await self._api_query('user_transactions', data=params)
            
            if not response:
                break
            
            for transaction in response:
                try:
                    # Filter for asset movements
                    if transaction.get('type') not in USER_TRANSACTION_ASSET_MOVEMENT_TYPE:
                        continue
                    
                    # Parse timestamp
                    timestamp = deserialize_timestamp_from_bitstamp_date(transaction['datetime'])
                    
                    # Skip if outside time range
                    if timestamp < start_ts or timestamp > end_ts:
                        continue
                    
                    # Determine category
                    tx_type = transaction['type']
                    category = AssetMovementCategory.DEPOSIT if tx_type == 0 else AssetMovementCategory.WITHDRAWAL
                    
                    # Find asset and amount
                    asset = None
                    amount = None
                    
                    for key, value in transaction.items():
                        if key in ('datetime', 'id', 'type', 'fee'):
                            continue
                        
                        # Keys are like 'btc' for the amount
                        try:
                            test_amount = FVal(value)
                            if test_amount != ZERO:
                                asset = asset_from_bitstamp(key.upper())
                                amount = abs(test_amount)
                                break
                        except:
                            continue
                    
                    if not asset or not amount:
                        logger.warning(f'Could not parse Bitstamp movement {transaction}')
                        continue
                    
                    # Parse fee
                    fee = deserialize_fee(transaction.get('fee', '0'))
                    
                    movement = AssetMovement(
                        location=Location.BITSTAMP,
                        category=category,
                        timestamp=timestamp,
                        address=None,  # Bitstamp doesn't provide addresses in this endpoint
                        transaction_id=None,
                        asset=asset,
                        amount=amount,
                        fee_asset=asset,
                        fee=fee,
                        link=str(transaction['id']),
                    )
                    movements.append(movement)
                    
                except Exception as e:
                    logger.warning(f'Failed to parse Bitstamp movement: {e}')
                    continue
            
            # Check if we need to query more
            if len(response) < API_MAX_LIMIT:
                break
            
            # Update since_id for next query
            last_id = response[-1]['id']
            params['since_id'] = last_id + 1
        
        return movements