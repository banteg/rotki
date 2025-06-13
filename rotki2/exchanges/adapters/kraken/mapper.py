"""Kraken data mapper adapter implementation."""
import logging
from decimal import Decimal
from typing import Any

from rotki2.assets.base import Asset
from rotki2.assets.converters import asset_from_kraken
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
    deserialize_timestamp,
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


class KrakenDataMapper(ExchangeDataMapperPort):
    """Kraken data mapper adapter.
    
    Transforms raw Kraken API responses into Rotki domain models.
    """
    
    def to_balances(self, raw_data: list[dict[str, Any]]) -> dict[Asset, AssetAmount]:
        """Transform raw balance data into Rotki balance format.
        
        Kraken balance format:
        {
            'asset': 'XXBT',  # Kraken uses X prefix for crypto
            'balance': '1.2345'
        }
        """
        balances: dict[Asset, AssetAmount] = {}
        
        for entry in raw_data:
            try:
                # Get asset symbol
                kraken_asset = entry.get('asset', '')
                if not kraken_asset:
                    continue
                    
                # Convert to Rotki asset
                try:
                    asset = asset_from_kraken(kraken_asset)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Kraken balance for unknown asset {kraken_asset}',
                        error=str(e),
                    )
                    continue
                
                # Parse balance
                balance = deserialize_asset_amount(entry.get('balance', '0'))
                
                if asset in balances:
                    balances[asset] += balance
                else:
                    balances[asset] = balance
                    
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Kraken balance entry',
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
        
        Kraken trade format:
        {
            'id': 'TXYZ123',
            'ordertxid': 'OXYZ123',
            'pair': 'XXBTZUSD',
            'time': 1234567890.123,
            'type': 'buy',
            'ordertype': 'limit',
            'price': '50000.1',
            'cost': '100.02',
            'fee': '0.26',
            'vol': '0.002',
            'margin': '0.0',
            'misc': ''
        }
        """
        trades = []
        
        for entry in raw_data:
            try:
                # Parse pair (e.g., 'XXBTZUSD' -> BTC/USD)
                pair = entry.get('pair', '')
                if not pair:
                    log.warning('Kraken trade missing pair', trade=entry)
                    continue
                    
                # Kraken pairs need special parsing
                base_asset, quote_asset = self._parse_kraken_pair(pair)
                if not base_asset or not quote_asset:
                    continue
                    
                # Parse amounts
                amount = deserialize_asset_amount(entry.get('vol', '0'))
                price = deserialize_price(entry.get('price', '0'))
                fee_amount = deserialize_fee(entry.get('fee', '0'))
                
                # Parse timestamp (Kraken uses float seconds)
                timestamp = deserialize_timestamp(entry.get('time', 0))
                
                # Determine trade type
                trade_type_str = entry.get('type', '').lower()
                if trade_type_str == 'buy':
                    trade_type = TradeType.BUY
                elif trade_type_str == 'sell':
                    trade_type = TradeType.SELL
                else:
                    log.warning(f'Unknown Kraken trade type: {trade_type_str}')
                    continue
                
                # Fee currency is always the quote currency in Kraken
                fee_currency = quote_asset
                
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
                    fee_currency=fee_currency if fee_amount > ZERO else None,
                    link=entry.get('id', ''),
                )
                
                trades.append(trade)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Kraken trade',
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
        """Transform raw ledger data into AssetMovement objects.
        
        Kraken ledger format:
        {
            'id': 'LXYZ123',
            'refid': 'RXYZ123',
            'time': 1234567890.123,
            'type': 'deposit' or 'withdrawal',
            'aclass': 'currency',
            'asset': 'XXBT',
            'amount': '0.1234',
            'fee': '0.0001',
            'balance': '1.2345'
        }
        """
        movements = []
        
        # Process deposits
        for entry in deposits:
            try:
                # Convert asset
                kraken_asset = entry.get('asset', '')
                try:
                    asset = asset_from_kraken(kraken_asset)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Kraken deposit with unknown asset {kraken_asset}',
                        error=str(e),
                    )
                    continue
                
                # Parse amounts
                amount = deserialize_asset_amount(entry.get('amount', '0'))
                fee = deserialize_fee(entry.get('fee', '0'))
                
                # Parse timestamp
                timestamp = deserialize_timestamp(entry.get('time', 0))
                
                movement = AssetMovement(
                    timestamp=timestamp,
                    location=location,
                    category=AssetMovementCategory.DEPOSIT,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=Fee(fee) if fee > ZERO else Fee(ZERO),
                    link=entry.get('refid', entry.get('id', '')),
                )
                
                movements.append(movement)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Kraken deposit',
                    deposit=entry,
                    error=str(e),
                )
                continue
        
        # Process withdrawals
        for entry in withdrawals:
            try:
                # Convert asset
                kraken_asset = entry.get('asset', '')
                try:
                    asset = asset_from_kraken(kraken_asset)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Kraken withdrawal with unknown asset {kraken_asset}',
                        error=str(e),
                    )
                    continue
                
                # Parse amounts (withdrawal amounts are negative in Kraken)
                amount_str = entry.get('amount', '0')
                amount = deserialize_asset_amount(amount_str.lstrip('-'))
                fee = deserialize_fee(entry.get('fee', '0'))
                
                # Parse timestamp
                timestamp = deserialize_timestamp(entry.get('time', 0))
                
                movement = AssetMovement(
                    timestamp=timestamp,
                    location=location,
                    category=AssetMovementCategory.WITHDRAWAL,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=Fee(fee) if fee > ZERO else Fee(ZERO),
                    link=entry.get('refid', entry.get('id', '')),
                )
                
                movements.append(movement)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Kraken withdrawal',
                    withdrawal=entry,
                    error=str(e),
                )
                continue
                
        return movements
    
    def map_asset(self, exchange_symbol: str) -> Asset | None:
        """Map Kraken asset symbol to Rotki Asset."""
        try:
            return asset_from_kraken(exchange_symbol)
        except (UnknownAsset, UnsupportedAsset):
            return None
    
    def _parse_kraken_pair(self, pair: str) -> tuple[Asset | None, Asset | None]:
        """Parse a Kraken trading pair into base and quote assets.
        
        Kraken uses prefixes like X for crypto and Z for fiat.
        Example: 'XXBTZUSD' -> (BTC, USD)
        """
        # Try to use Kraken's pair info if available
        # For now, use simple heuristics
        
        # Known patterns
        crypto_prefixes = ['X', 'XX']
        fiat_prefixes = ['Z', 'ZZ']
        
        # Try different split points
        for i in range(3, len(pair) - 2):
            base_part = pair[:i]
            quote_part = pair[i:]
            
            try:
                base_asset = asset_from_kraken(base_part)
                quote_asset = asset_from_kraken(quote_part)
                return base_asset, quote_asset
            except (UnknownAsset, UnsupportedAsset):
                continue
                
        log.warning(f'Could not parse Kraken pair: {pair}')
        return None, None