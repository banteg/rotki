"""Binance exchange implementation"""
import hashlib
import hmac
import json
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlencode

import anyio

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    AssetMovementCategory,
    BinancePair,
    MarginPosition,
    Trade,
    TradeType,
)
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp_from_intms,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    Location,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now_in_ms
from rotki2.exchanges.base import ExchangeInterface, ExchangeWithExtras
from rotki2.exchanges.utils import (
    deserialize_asset_from_exchange,
    handle_unknown_asset,
    paginated_query_loop,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = RotkehlchenLogsAdapter(__name__)

# Binance launched at 2017-07-14T04:00:00Z
BINANCE_LAUNCH_TS: Final = Timestamp(1500001200)
API_TIME_INTERVAL_CONSTRAINT_TS: Final = 7689600  # 89 days

V3_METHODS: Final = (
    'account',
    'myTrades',
    'openOrders',
    'exchangeInfo',
    'time',
)
PUBLIC_METHODS: Final = ('exchangeInfo', 'time')

BINANCE_API_TYPE = Literal['api', 'sapi', 'dapi', 'fapi']
BINANCE_BASE_URL: Final = 'https://api.binance.com'
BINANCEUS_BASE_URL: Final = 'https://api.binance.us'


class BinancePermissionError(RemoteError):
    """Exception raised when a binance permission problem is detected"""


class Binance(ExchangeInterface, ExchangeWithExtras):
    """Binance exchange implementation
    
    Supports both Binance.com and Binance.us
    """
    
    def __init__(
        self,
        name: str,
        api_key: ApiKey,
        secret: ApiSecret,
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
        binance_markets: list[str] | None = None,
        uri: str = BINANCE_BASE_URL,
    ):
        location = Location.BINANCE if uri == BINANCE_BASE_URL else Location.BINANCEUS
        super().__init__(
            name=name,
            location=location,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.uri = uri
        self.binance_markets = binance_markets or []
        
        # Binance rate limits: 1200 requests per minute (weight-based)
        self.rate_limit_calls = 1200
        self.rate_limit_period = 60
        
        # Cache for trading pairs
        self._symbols_to_pair: dict[str, BinancePair] | None = None
        self._last_symbols_update = 0
    
    def get_extras(self) -> dict[str, Any]:
        """Get Binance-specific extras"""
        return {'binance_markets': self.binance_markets}
    
    def set_extras(self, extras: dict[str, Any]) -> None:
        """Set Binance-specific extras"""
        if 'binance_markets' in extras:
            self.binance_markets = extras['binance_markets']
    
    def _generate_signature(self, query_str: str) -> str:
        """Generate signature for authenticated requests"""
        return hmac.new(
            self.secret.encode('utf-8'),
            query_str.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
    
    async def _api_query(
        self,
        api_type: BINANCE_API_TYPE,
        method: str,
        options: dict[str, Any] | None = None,
        http_method: Literal['GET', 'POST', 'DELETE'] = 'GET',
    ) -> dict[str, Any]:
        """Query Binance API"""
        if options is None:
            options = {}
        
        # Construct URL
        if api_type == 'api':
            api_version = 'v3' if method in V3_METHODS else 'v1'
            url = f'{self.uri}/api/{api_version}/{method}'
        else:
            url = f'{self.uri}/{api_type}/v1/{method}'
        
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Add authentication if needed
        if method not in PUBLIC_METHODS:
            options['timestamp'] = ts_now_in_ms()
            options['recvWindow'] = 10000
            
            # Create query string and signature
            query_str = urlencode(options)
            options['signature'] = self._generate_signature(query_str)
            
            headers = {'X-MBX-APIKEY': self.api_key}
        else:
            headers = {}
        
        # Make request
        try:
            if http_method == 'GET':
                response = await self.http_client.get(url, params=options, headers=headers)
            elif http_method == 'POST':
                response = await self.http_client.post(url, data=options, headers=headers)
            else:  # DELETE
                response = await self.http_client.delete(url, params=options, headers=headers)
            
            if response.status_code != 200:
                raise RemoteError(
                    f'Binance API request failed with status {response.status_code}: '
                    f'{response.text}'
                )
            
            result = response.json()
            
            # Check for API errors
            if 'code' in result:
                raise RemoteError(f'Binance API error: {result}')
            
            return result
            
        except json.JSONDecodeError as e:
            raise RemoteError(f'Invalid JSON response from Binance: {e}') from e
    
    async def validate_api_key(self) -> tuple[bool, str]:
        """Validate API credentials"""
        try:
            await self._api_query('api', 'account')
            return True, ''
        except RemoteError as e:
            error_str = str(e)
            if 'Invalid API-key' in error_str:
                return False, 'Invalid API key'
            elif 'Signature for this request is not valid' in error_str:
                return False, 'Invalid API secret'
            elif 'Timestamp for this request' in error_str:
                return False, 'System time mismatch - please sync your clock'
            else:
                return False, f'API validation failed: {error_str}'
    
    async def _update_symbols_to_pair(self) -> None:
        """Update the symbols to pair mapping"""
        # Cache for 1 hour
        if self._symbols_to_pair and ts_now_in_ms() - self._last_symbols_update < 3600000:
            return
        
        response = await self._api_query('api', 'exchangeInfo')
        
        self._symbols_to_pair = {}
        for symbol_data in response.get('symbols', []):
            if symbol_data['status'] != 'TRADING':
                continue
            
            symbol = symbol_data['symbol']
            base_asset = asset_from_binance(symbol_data['baseAsset'])
            quote_asset = asset_from_binance(symbol_data['quoteAsset'])
            
            if base_asset and quote_asset:
                self._symbols_to_pair[symbol] = BinancePair(
                    symbol=symbol,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                )
        
        self._last_symbols_update = ts_now_in_ms()
    
    async def query_balances(self, **kwargs: Any) -> dict[Asset, Balance]:
        """Query account balances"""
        response = await self._api_query('api', 'account')
        
        balances = {}
        for balance_data in response.get('balances', []):
            try:
                asset_name = balance_data['asset']
                free = FVal(balance_data['free'])
                locked = FVal(balance_data['locked'])
                
                amount = free + locked
                if amount <= ZERO:
                    continue
                
                asset = asset_from_binance(asset_name)
                if not asset:
                    continue
                
                # Get USD value
                try:
                    usd_price = await self._get_asset_usd_price(asset)
                    usd_value = amount * usd_price
                except Exception:
                    usd_value = ZERO
                
                balances[asset] = Balance(amount=amount, usd_value=usd_value)
                
            except (ValueError, KeyError) as e:
                logger.warning(f'Failed to process Binance balance: {e}')
                continue
        
        return balances
    
    async def query_online_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history"""
        # Update symbols mapping
        await self._update_symbols_to_pair()
        
        if not self._symbols_to_pair:
            return []
        
        trades = []
        
        # Query trades for selected markets
        markets_to_query = self.binance_markets if self.binance_markets else list(self._symbols_to_pair.keys())
        
        for symbol in markets_to_query:
            if symbol not in self._symbols_to_pair:
                continue
            
            pair = self._symbols_to_pair[symbol]
            
            # Binance limits: max 1000 trades per request
            options = {
                'symbol': symbol,
                'limit': 1000,
                'startTime': start_ts * 1000,
                'endTime': end_ts * 1000,
            }
            
            try:
                response = await self._api_query('api', 'myTrades', options)
                
                for trade_data in response:
                    try:
                        is_buy = trade_data['isBuyer']
                        amount = deserialize_asset_amount(trade_data['qty'])
                        rate = deserialize_price(trade_data['price'])
                        fee = deserialize_fee(trade_data['commission'])
                        fee_asset = asset_from_binance(trade_data['commissionAsset'])
                        
                        trade = Trade(
                            timestamp=deserialize_timestamp_from_intms(trade_data['time']),
                            location=self.location,
                            base_asset=pair.base_asset,
                            quote_asset=pair.quote_asset,
                            trade_type=TradeType.BUY if is_buy else TradeType.SELL,
                            amount=amount,
                            rate=rate,
                            fee=fee,
                            fee_currency=fee_asset,
                            link=str(trade_data['id']),
                        )
                        trades.append(trade)
                        
                    except Exception as e:
                        logger.warning(f'Failed to parse Binance trade: {e}')
                        continue
                        
            except RemoteError as e:
                logger.warning(f'Failed to query trades for {symbol}: {e}')
                continue
        
        return trades
    
    async def query_online_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals"""
        movements = []
        
        # Query deposits
        deposit_options = {
            'startTime': start_ts * 1000,
            'endTime': end_ts * 1000,
        }
        
        try:
            deposits = await self._api_query('sapi', 'capital/deposit/hisrec', deposit_options)
            
            for deposit in deposits:
                try:
                    asset = asset_from_binance(deposit['coin'])
                    if not asset:
                        continue
                    
                    movement = AssetMovement(
                        location=self.location,
                        category=AssetMovementCategory.DEPOSIT,
                        timestamp=deserialize_timestamp_from_intms(deposit['insertTime']),
                        address=deposit.get('address'),
                        transaction_id=deposit.get('txId'),
                        asset=asset,
                        amount=deserialize_asset_amount(deposit['amount']),
                        fee_asset=asset,
                        fee=ZERO,  # Binance doesn't charge deposit fees
                        link=deposit.get('id', ''),
                    )
                    movements.append(movement)
                    
                except Exception as e:
                    logger.warning(f'Failed to parse Binance deposit: {e}')
                    continue
                    
        except RemoteError as e:
            logger.warning(f'Failed to query Binance deposits: {e}')
        
        # Query withdrawals
        withdrawal_options = {
            'startTime': start_ts * 1000,
            'endTime': end_ts * 1000,
        }
        
        try:
            withdrawals = await self._api_query('sapi', 'capital/withdraw/history', withdrawal_options)
            
            for withdrawal in withdrawals:
                try:
                    asset = asset_from_binance(withdrawal['coin'])
                    if not asset:
                        continue
                    
                    movement = AssetMovement(
                        location=self.location,
                        category=AssetMovementCategory.WITHDRAWAL,
                        timestamp=deserialize_timestamp_from_intms(withdrawal['applyTime']),
                        address=withdrawal.get('address'),
                        transaction_id=withdrawal.get('txId'),
                        asset=asset,
                        amount=deserialize_asset_amount(withdrawal['amount']),
                        fee_asset=asset,
                        fee=deserialize_fee(withdrawal.get('transactionFee', '0')),
                        link=withdrawal.get('id', ''),
                    )
                    movements.append(movement)
                    
                except Exception as e:
                    logger.warning(f'Failed to parse Binance withdrawal: {e}')
                    continue
                    
        except RemoteError as e:
            logger.warning(f'Failed to query Binance withdrawals: {e}')
        
        return movements
    
    async def _get_asset_usd_price(self, asset: Asset) -> FVal:
        """Get USD price for an asset"""
        # Simplified - would integrate with price oracle
        return FVal('1')
    
    async def get_all_pairs(self) -> list[str]:
        """Get all available trading pairs"""
        await self._update_symbols_to_pair()
        return list(self._symbols_to_pair.keys()) if self._symbols_to_pair else []