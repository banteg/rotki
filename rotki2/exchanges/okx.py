"""OKX exchange implementation"""
import base64
import hashlib
import hmac
import json
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode, urljoin

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_okx
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    AssetMovementCategory,
    Trade,
    TradeType,
)
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
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
    ExchangeAuthCredentials,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now_in_ms, ts_sec_to_ms
from rotki2.exchanges.base import ExchangeInterface, ExchangeWithoutApiSecret

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = RotkehlchenLogsAdapter(__name__)


class OkxEndpoint(Enum):
    """OKX API endpoints"""
    CURRENCIES = '/api/v5/asset/currencies'
    TRADING_BALANCE = '/api/v5/account/balance'
    FUNDING_BALANCE = '/api/v5/asset/balances'
    TRADES = '/api/v5/trade/orders-history-archive'
    DEPOSITS = '/api/v5/asset/deposit-history'
    WITHDRAWALS = '/api/v5/asset/withdrawal-history'


class OKX(ExchangeInterface):
    """OKX exchange implementation
    
    All operations are async. Maintains compatibility with the
    original OKX exchange functionality.
    
    API docs: https://www.okx.com/docs-v5
    """
    
    # Maximum results returned by an OKX API request
    MAX_RESULTS = 100
    
    def __init__(
        self,
        name: str,
        api_key: ApiKey,
        secret: ApiSecret,
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
        passphrase: str,
    ):
        super().__init__(
            name=name,
            location=Location.OKX,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.passphrase = passphrase
        self.base_uri = 'https://www.okx.com/'
        
        # Set OKX-specific rate limits
        self.rate_limit_calls = 60
        self.rate_limit_period = 2  # 60 calls per 2 seconds
        
    def _generate_signature(
        self,
        timestamp: str,
        method: Literal['GET', 'POST', 'PUT', 'DELETE'],
        path: str,
        body: str = '',
    ) -> str:
        """Generate OKX API signature
        
        https://www.okx.com/docs-v5/en/#rest-api-authentication-signature
        """
        prehash = timestamp + method + path + body
        signature = hmac.new(
            self.secret, 
            prehash.encode('utf-8'), 
            hashlib.sha256
        )
        return base64.b64encode(signature.digest()).decode('utf-8')
    
    async def _api_query(
        self,
        endpoint: OkxEndpoint,
        options: dict[str, Any] | None = None,
        method: Literal['GET', 'POST'] = 'GET',
    ) -> dict[str, Any]:
        """Make an API query to OKX
        
        May raise:
        - RemoteError if request fails or returns invalid JSON
        """
        options = options.copy() if options else {}
        
        # Build query parameters
        params = {}
        if endpoint in {OkxEndpoint.TRADES, OkxEndpoint.DEPOSITS, OkxEndpoint.WITHDRAWALS}:
            # supports pagination
            params.update({
                'limit': str(options.get('limit', self.MAX_RESULTS)),
            })
            if 'after' in options:
                params['after'] = str(options['after'])
        
        if endpoint == OkxEndpoint.TRADES:
            params.update({
                'instType': 'SPOT',
                'state': 'filled',
            })
            if options.get('start_ts'):
                params['begin'] = str(ts_sec_to_ms(Timestamp(int(options['start_ts']))))
            if options.get('end_ts'):
                params['end'] = str(ts_sec_to_ms(Timestamp(int(options['end_ts']))))
        
        # Build path with query parameters
        path = endpoint.value
        if params:
            path += f'?{urlencode(params)}'
        
        # Generate timestamp and signature
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        signature = self._generate_signature(timestamp, method, path)
        
        # Build headers
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json',
        }
        
        # Make request
        url = urljoin(self.base_uri, path)
        
        try:
            async with self._rate_limit_lock:
                await self._ensure_rate_limit()
                
                if method == 'GET':
                    response = await self.http_client.get(url, headers=headers)
                else:
                    response = await self.http_client.post(url, headers=headers)
                
                self.call_counter += 1
                
        except Exception as e:
            raise RemoteError(f'{self.name} API request failed due to {e!s}') from e
        
        # Parse response
        try:
            json_response = response.json()
        except Exception as e:
            raise RemoteError(
                f'{self.name} returned invalid JSON response: {response.text}'
            ) from e
        
        # Check for API errors
        if json_response.get('code') != '0':
            error_msg = json_response.get('msg', 'Unknown error')
            raise RemoteError(f'{self.name} API error: {error_msg}')
        
        return json_response
    
    async def _api_query_list(
        self,
        endpoint: OkxEndpoint,
        options: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Make an API query and parse the response into a list
        
        May raise:
        - RemoteError if the API returns an unexpected response
        """
        response = await self._api_query(endpoint=endpoint, options=options)
        data = response.get('data')
        if data is None or not isinstance(data, list):
            raise RemoteError(
                f'{self.name} json response does not contain list `data`: {response}'
            )
        return data
    
    async def _api_query_list_paginated(
        self,
        endpoint: OkxEndpoint,
        pagination_key: str,
        options: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Make paginated API queries
        
        Makes subsequent API queries until response list length is less than MAX_RESULTS.
        Pagination is handled by setting `pagination_key` value in the `after` query parameter.
        
        May raise:
        - RemoteError if the API returns an unexpected response
        """
        options = options.copy() if options else {}
        all_items = []
        
        while True:
            data = await self._api_query_list(endpoint=endpoint, options=options)
            all_items.extend(data)
            
            if len(data) < self.MAX_RESULTS:
                break
            
            # Get the pagination value from the last item
            earliest_item = data[-1]
            options['after'] = earliest_item.get(pagination_key)
            if not options['after']:
                break
        
        return all_items
    
    async def validate_api_key(self) -> tuple[bool, str]:
        """Validate API credentials"""
        try:
            await self._api_query(endpoint=OkxEndpoint.TRADING_BALANCE)
            return True, ''
        except RemoteError as e:
            return False, str(e)
    
    async def first_connection(self) -> None:
        """Called on first connection to validate credentials"""
        if self.first_connection_made:
            return
            
        success, msg = await self.validate_api_key()
        if not success:
            raise RemoteError(f'Failed to validate {self.name} API credentials: {msg}')
        
        self.first_connection_made = True
    
    async def query_balances(self, **kwargs: Any) -> dict[Asset, Balance]:
        """Query account balances
        
        https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance
        https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-balance
        
        May raise:
        - RemoteError if the OKX API returns an unexpected response
        """
        # Ensure we're connected
        await self.first_connection()
        
        # Get trading account balance
        currencies_data: list[dict[str, Any]] = []
        data = await self._api_query_list(endpoint=OkxEndpoint.TRADING_BALANCE)
        if not (len(data) == 1 and isinstance(data[0], dict)):
            raise RemoteError(
                f'{self.name} trading balance response does not contain dict data[0]'
            )
        
        try:
            currencies_data.extend(data[0]['details'])
        except KeyError as e:
            msg = f'Missing key: {e!s}'
            raise RemoteError(
                f'{self.name} trading balance API request failed due to unexpected response {msg}'
            ) from e
        
        # Get funding account balance
        funding_data = await self._api_query_list(endpoint=OkxEndpoint.FUNDING_BALANCE)
        currencies_data.extend(funding_data)
        
        # Process balances
        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for currency_data in currencies_data:
            try:
                asset = asset_from_okx(okx_name=currency_data['ccy'])
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} balance with unknown asset '
                    f'{e.identifier}. Ignoring it.'
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} balance with unsupported asset '
                    f'{e.identifier}. Ignoring it.'
                )
                continue
            
            try:
                # Get available and frozen balance
                available = FVal(currency_data.get('availBal', '0'))
                frozen = FVal(currency_data.get('frozenBal', '0'))
                amount = available + frozen
                
                if amount == ZERO:
                    continue
                
            except (ValueError, DeserializationError) as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} {asset.symbol} balance result due to '
                    f'inability to deserialize amount: {e!s}. Skipping balance.'
                )
                continue
            
            # Get USD price
            try:
                usd_price = Inquirer.find_usd_price(asset=asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} {asset.symbol} balance result due to '
                    f'inability to query USD price: {e!s}. Skipping balance.'
                )
                continue
            
            assets_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )
        
        return dict(assets_balance)
    
    async def query_online_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history
        
        https://www.okx.com/docs-v5/en/#rest-api-trade-get-order-history-last-3-months
        
        May raise:
        - RemoteError from _api_query_list_paginated
        """
        # Ensure we're connected
        await self.first_connection()
        
        raw_trades = await self._api_query_list_paginated(
            endpoint=OkxEndpoint.TRADES,
            pagination_key='ordId',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )
        
        trades: list[Trade] = []
        for raw_trade in raw_trades:
            trade = self._deserialize_trade(raw_trade)
            if trade:
                trades.append(trade)
        
        return trades
    
    def _deserialize_trade(self, raw_trade: dict[str, Any]) -> Trade | None:
        """Deserialize a raw trade from OKX
        
        Returns None if there's an error during deserialization
        """
        try:
            # Parse instrument ID to get base and quote assets
            inst_id = raw_trade['instId']
            base_asset_str, quote_asset_str = inst_id.split('-')
            base_asset = asset_from_okx(base_asset_str)
            quote_asset = asset_from_okx(quote_asset_str)
            
            # Parse trade data
            timestamp = TimestampMS(int(raw_trade['cTime'])) // 1000
            trade_type = TradeType.BUY if raw_trade['side'] == 'buy' else TradeType.SELL
            amount = deserialize_asset_amount(raw_trade['accFillSz'])
            rate = deserialize_price(raw_trade['avgPx'])
            
            # Parse fee
            fee_amount = FVal(raw_trade.get('fee', '0'))
            # OKX represents fees as negative numbers
            if fee_amount < ZERO:
                fee_amount = -fee_amount
            
            fee_currency = asset_from_okx(raw_trade['feeCcy']) if raw_trade.get('feeCcy') else None
            fee = deserialize_fee(fee_amount) if fee_currency else None
            
            return Trade(
                timestamp=timestamp,
                location=self.location,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=trade_type,
                amount=amount,
                rate=rate,
                fee=fee,
                fee_currency=fee_currency,
                link=raw_trade['ordId'],
            )
            
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} trade with unknown asset {e.identifier}. Ignoring it.'
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} trade with unsupported asset {e.identifier}. Ignoring it.'
            )
        except (KeyError, ValueError, DeserializationError) as e:
            self.msg_aggregator.add_error(
                f'Error deserializing {self.name} trade: {e!s}. Skipping trade.'
            )
            logger.error(
                f'Failed to deserialize {self.name} trade',
                raw_trade=raw_trade,
                error=str(e),
            )
        
        return None
    
    async def query_online_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals
        
        https://www.okx.com/docs-v5/en/#rest-api-funding-get-deposit-history
        https://www.okx.com/docs-v5/en/#rest-api-funding-get-withdrawal-history
        
        May raise:
        - RemoteError from _api_query_list_paginated
        """
        # Ensure we're connected
        await self.first_connection()
        
        # Query deposits
        deposits = await self._api_query_list_paginated(
            endpoint=OkxEndpoint.DEPOSITS,
            pagination_key='ts',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )
        
        # Query withdrawals
        withdrawals = await self._api_query_list_paginated(
            endpoint=OkxEndpoint.WITHDRAWALS,
            pagination_key='ts',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )
        
        movements: list[AssetMovement] = []
        
        # Process deposits
        for raw_deposit in deposits:
            movement = self._deserialize_asset_movement(
                raw_deposit,
                AssetMovementCategory.DEPOSIT,
            )
            if movement:
                movements.append(movement)
        
        # Process withdrawals
        for raw_withdrawal in withdrawals:
            movement = self._deserialize_asset_movement(
                raw_withdrawal,
                AssetMovementCategory.WITHDRAWAL,
            )
            if movement:
                movements.append(movement)
        
        return movements
    
    def _deserialize_asset_movement(
        self,
        raw_movement: dict[str, Any],
        category: AssetMovementCategory,
    ) -> AssetMovement | None:
        """Deserialize a raw asset movement from OKX
        
        Returns None if there's an error during deserialization
        """
        try:
            asset = asset_from_okx(raw_movement['ccy'])
            timestamp = TimestampMS(int(raw_movement['ts'])) // 1000
            amount = deserialize_asset_amount(raw_movement['amt'])
            
            # Get fee for withdrawals
            fee = None
            fee_asset = None
            if category == AssetMovementCategory.WITHDRAWAL and raw_movement.get('fee'):
                fee = deserialize_fee(raw_movement['fee'])
                fee_asset = asset
            
            # Extract address and transaction ID
            address = raw_movement.get('to', '')
            transaction_id = raw_movement.get('txId', '')
            
            return AssetMovement(
                location=self.location,
                category=category,
                timestamp=timestamp,
                address=address,
                transaction_id=transaction_id,
                asset=asset,
                amount=amount,
                fee_asset=fee_asset,
                fee=fee,
                link=transaction_id,
            )
            
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} {category.name.lower()} with unknown asset '
                f'{e.identifier}. Ignoring it.'
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} {category.name.lower()} with unsupported asset '
                f'{e.identifier}. Ignoring it.'
            )
        except (KeyError, ValueError, DeserializationError) as e:
            self.msg_aggregator.add_error(
                f'Error deserializing {self.name} {category.name.lower()}: {e!s}. '
                f'Skipping movement.'
            )
            logger.error(
                f'Failed to deserialize {self.name} {category.name.lower()}',
                raw_movement=raw_movement,
                error=str(e),
            )
        
        return None
    
    async def query_online_margin_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[MarginPosition]:
        """Query margin history - not supported for OKX"""
        return []
    
    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        """Edit exchange credentials"""
        changed = super().edit_exchange_credentials(credentials)
        if credentials.passphrase is not None:
            self.passphrase = credentials.passphrase
            changed = True
        return changed
    
    async def close(self) -> None:
        """Close the exchange connection"""
        # Close HTTP client if we own it
        if hasattr(self, '_owns_http_client') and self._owns_http_client:
            await self.http_client.close()