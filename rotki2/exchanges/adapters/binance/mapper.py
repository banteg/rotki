"""Binance data mapper adapter implementation."""
import logging
from decimal import Decimal
from typing import Any

from rotki2.assets.base import Asset
from rotki2.assets.converters import asset_from_binance
from rotki2.constants import ZERO
from rotki2.errors.asset import UnknownAsset, UnsupportedAsset
from rotki2.errors.serialization import DeserializationError
from rotki2.exchanges.ports import ExchangeDataMapperPort
from rotki2.history.events.structures.asset import AssetMovement
from rotki2.history.events.structures.exchange import Trade
from rotki2.logging import RotkehlchenLogsAdapter
from rotki2.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp_from_intms,
)
from rotki2.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BinanceDataMapper(ExchangeDataMapperPort):
    """Binance data mapper adapter.
    
    Transforms raw Binance API responses into Rotki domain models.
    """
    
    def to_balances(self, raw_data: list[dict[str, Any]]) -> dict[Asset, AssetAmount]:
        """Transform raw balance data into Rotki balance format.
        
        Binance balance format:
        {
            'asset': 'BTC',
            'free': '0.1',
            'locked': '0.05'
        }
        """
        balances: dict[Asset, AssetAmount] = {}
        
        for entry in raw_data:
            try:
                # Get asset symbol
                symbol = entry.get('asset', '')
                if not symbol:
                    continue
                    
                # Convert to Rotki asset
                try:
                    asset = asset_from_binance(symbol)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Binance balance for unknown asset {symbol}',
                        error=str(e),
                    )
                    continue
                
                # Sum free and locked amounts
                free = deserialize_asset_amount(entry.get('free', '0'))
                locked = deserialize_asset_amount(entry.get('locked', '0'))
                total = free + locked
                
                if total > ZERO:
                    balances[asset] = total
                    
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Binance balance entry',
                    entry=entry,
                    error=str(e),
                )
                continue
                
        return balances
    
    def to_trades(
        self,
        raw_data: list[dict[str, Any]],
        location: Location,
    ) -> list[Trade]:
        """Transform raw trade data into Rotki Trade objects.
        
        Binance trade format:
        {
            'symbol': 'BTCUSDT',
            'id': 123456,
            'orderId': 789012,
            'price': '50000.00',
            'qty': '0.001',
            'quoteQty': '50.00',
            'commission': '0.00005',
            'commissionAsset': 'BTC',
            'time': 1234567890123,
            'isBuyer': true,
            'isMaker': false,
            'isBestMatch': true
        }
        """
        trades = []
        
        for entry in raw_data:
            try:
                # Parse symbol into base/quote assets
                symbol = entry.get('symbol', '')
                base_asset, quote_asset = self._parse_binance_symbol(symbol)
                
                if not base_asset or not quote_asset:
                    log.warning(f'Could not parse Binance symbol: {symbol}')
                    continue
                
                # Parse amounts
                amount = deserialize_asset_amount(entry.get('qty', '0'))
                price = deserialize_price(entry.get('price', '0'))
                
                # Parse fee
                fee_amount = deserialize_fee(entry.get('commission', '0'))
                fee_asset_str = entry.get('commissionAsset', '')
                
                try:
                    fee_asset = asset_from_binance(fee_asset_str) if fee_asset_str else None
                except (UnknownAsset, UnsupportedAsset):
                    fee_asset = None
                    
                # Parse timestamp (milliseconds)
                timestamp = deserialize_timestamp_from_intms(entry.get('time', 0))
                
                # Determine trade type
                is_buyer = entry.get('isBuyer', False)
                trade_type = TradeType.BUY if is_buyer else TradeType.SELL
                
                # Create trade
                trade = Trade(
                    timestamp=timestamp,
                    location=location,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    trade_type=trade_type,
                    amount=amount,
                    rate=price,
                    fee=Fee(fee_amount) if fee_amount > ZERO else None,
                    fee_currency=fee_asset,
                    link=str(entry.get('id', '')),
                )
                
                trades.append(trade)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Binance trade',
                    trade=entry,
                    error=str(e),
                )
                continue
                
        return trades
    
    def to_asset_movements(
        self,
        deposits: list[dict[str, Any]],
        withdrawals: list[dict[str, Any]],
        location: Location,
    ) -> list[AssetMovement]:
        """Transform raw deposit/withdrawal data into AssetMovement objects.
        
        Binance deposit format:
        {
            'amount': '0.001',
            'coin': 'BTC',
            'network': 'BTC',
            'status': 1,
            'address': '1A1zP1...',
            'addressTag': '',
            'txId': 'abc123...',
            'insertTime': 1234567890000,
            'transferType': 0,
            'confirmTimes': '6/6'
        }
        
        Binance withdrawal format:
        {
            'id': 'abc123',
            'amount': '0.001',
            'transactionFee': '0.0001',
            'coin': 'BTC',
            'status': 6,
            'address': '1A1zP1...',
            'txId': 'def456...',
            'applyTime': '2021-01-01 00:00:00',
            'network': 'BTC',
            'transferType': 0
        }
        """
        movements = []
        
        # Process deposits
        for entry in deposits:
            try:
                # Only process completed deposits (status = 1)
                if entry.get('status') != 1:
                    continue
                    
                # Convert asset
                coin = entry.get('coin', '')
                try:
                    asset = asset_from_binance(coin)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Binance deposit with unknown asset {coin}',
                        error=str(e),
                    )
                    continue
                
                # Parse amount
                amount = deserialize_asset_amount(entry.get('amount', '0'))
                
                # Parse timestamp (milliseconds)
                timestamp = deserialize_timestamp_from_intms(entry.get('insertTime', 0))
                
                movement = AssetMovement(
                    timestamp=timestamp,
                    location=location,
                    category=AssetMovementCategory.DEPOSIT,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=Fee(ZERO),  # Binance doesn't charge deposit fees
                    link=entry.get('txId', ''),
                )
                
                movements.append(movement)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Binance deposit',
                    deposit=entry,
                    error=str(e),
                )
                continue
        
        # Process withdrawals
        for entry in withdrawals:
            try:
                # Only process completed withdrawals (status = 6)
                if entry.get('status') != 6:
                    continue
                    
                # Convert asset
                coin = entry.get('coin', '')
                try:
                    asset = asset_from_binance(coin)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Binance withdrawal with unknown asset {coin}',
                        error=str(e),
                    )
                    continue
                
                # Parse amounts
                amount = deserialize_asset_amount(entry.get('amount', '0'))
                fee = deserialize_fee(entry.get('transactionFee', '0'))
                
                # Parse timestamp
                # Try different time fields
                timestamp = None
                if 'completeTime' in entry:
                    timestamp = deserialize_timestamp_from_intms(entry['completeTime'])
                elif 'applyTime' in entry:
                    # This is a string timestamp
                    from datetime import datetime
                    try:
                        dt = datetime.strptime(entry['applyTime'], '%Y-%m-%d %H:%M:%S')
                        timestamp = Timestamp(int(dt.timestamp()))
                    except ValueError:
                        pass
                        
                if not timestamp:
                    log.warning('Could not parse timestamp for Binance withdrawal')
                    continue
                
                movement = AssetMovement(
                    timestamp=timestamp,
                    location=location,
                    category=AssetMovementCategory.WITHDRAWAL,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=Fee(fee) if fee > ZERO else Fee(ZERO),
                    link=entry.get('txId', entry.get('id', '')),
                )
                
                movements.append(movement)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Binance withdrawal',
                    withdrawal=entry,
                    error=str(e),
                )
                continue
                
        return movements
    
    def map_asset(self, exchange_symbol: str) -> Asset | None:
        """Map Binance asset symbol to Rotki Asset."""
        try:
            return asset_from_binance(exchange_symbol)
        except (UnknownAsset, UnsupportedAsset):
            return None
    
    def _parse_binance_symbol(self, symbol: str) -> tuple[Asset | None, Asset | None]:
        """Parse a Binance trading pair into base and quote assets.
        
        Binance uses simple concatenation: BTCUSDT, ETHBTC, etc.
        """
        # Known quote currencies in order of preference
        quote_currencies = [
            'USDT', 'BUSD', 'USDC', 'TUSD', 'PAX', 'USD',
            'BTC', 'ETH', 'BNB', 'TRX', 'XRP', 'EUR', 'GBP',
        ]
        
        # Try each quote currency
        for quote in quote_currencies:
            if symbol.endswith(quote):
                base_str = symbol[:-len(quote)]
                
                try:
                    base_asset = asset_from_binance(base_str)
                    quote_asset = asset_from_binance(quote)
                    return base_asset, quote_asset
                except (UnknownAsset, UnsupportedAsset):
                    continue
                    
        log.warning(f'Could not parse Binance symbol: {symbol}')
        return None, None