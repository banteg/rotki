"""OKX data mapper adapter implementation.

This adapter handles transformation of raw OKX API data
into Rotki's internal domain models.
"""
import logging
from decimal import Decimal
from typing import Any

from rotki2.assets.base import Asset
from rotki2.assets.converters import asset_from_okx
from rotki2.constants import ZERO
from rotki2.errors.asset import UnknownAsset, UnsupportedAsset
from rotki2.errors.serialization import DeserializationError
from rotki2.exchanges.ports import ExchangeDataMapperPort
from rotki2.history.events.structures.asset import AssetMovement
from rotki2.history.events.structures.exchange import Trade
from rotki2.history.events.structures.types import HistoryEventSubType, HistoryEventType
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


class OkxDataMapper(ExchangeDataMapperPort):
    """OKX data mapper adapter.
    
    Implements the ExchangeDataMapperPort interface for OKX exchange.
    Transforms raw API responses into Rotki domain models.
    """
    
    def __init__(self) -> None:
        """Initialize the OKX data mapper."""
        self.location = Location.OKX
    
    def to_balances(self, raw_data: list[dict[str, Any]]) -> dict[Asset, AssetAmount]:
        """Transform raw balance data into Rotki balance format.
        
        OKX balance format:
        {
            'ccy': 'BTC',
            'availBal': '0.001',
            'bal': '0.001',
            'account_type': 'trading'  # Added by client
        }
        """
        balances: dict[Asset, AssetAmount] = {}
        
        for entry in raw_data:
            try:
                # Get currency symbol
                currency = entry.get('ccy')
                if not currency:
                    log.warning('Skipping OKX balance entry without currency', entry=entry)
                    continue
                
                # Convert to Rotki asset
                try:
                    asset = asset_from_okx(currency)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping OKX balance for unknown asset {currency}',
                        error=str(e),
                    )
                    continue
                
                # Get balance amount (use total balance, not just available)
                balance_str = entry.get('bal', '0')
                amount = deserialize_asset_amount(balance_str)
                
                # Aggregate balances from different account types
                if asset in balances:
                    balances[asset] += amount
                else:
                    balances[asset] = amount
                    
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize OKX balance entry',
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
        
        OKX trade format:
        {
            'instId': 'BTC-USDT',
            'ordId': '123456',
            'side': 'buy',
            'sz': '0.001',
            'px': '50000',
            'fee': '-0.00001',
            'feeCcy': 'BTC',
            'fillTime': '1234567890123'
        }
        """
        trades = []
        
        for entry in raw_data:
            try:
                # Parse instrument ID (e.g., 'BTC-USDT')
                inst_id = entry.get('instId', '')
                parts = inst_id.split('-')
                if len(parts) != 2:
                    log.warning(f'Invalid OKX instrument ID: {inst_id}')
                    continue
                    
                base_str, quote_str = parts
                
                # Convert assets
                try:
                    base_asset = asset_from_okx(base_str)
                    quote_asset = asset_from_okx(quote_str)
                    fee_asset = asset_from_okx(entry.get('feeCcy', ''))
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping OKX trade with unknown asset',
                        trade=entry,
                        error=str(e),
                    )
                    continue
                
                # Parse amounts
                amount = deserialize_asset_amount(entry.get('sz', '0'))
                price = deserialize_price(entry.get('px', '0'))
                
                # Parse fee (OKX uses negative values for fees)
                fee_str = entry.get('fee', '0')
                fee_amount = deserialize_fee(fee_str)
                if fee_amount < ZERO:
                    fee_amount = -fee_amount  # Convert to positive
                
                # Parse timestamp (milliseconds)
                timestamp = deserialize_timestamp_from_intms(entry.get('fillTime', 0))
                
                # Determine trade type
                side = entry.get('side', '').lower()
                if side == 'buy':
                    trade_type = TradeType.BUY
                elif side == 'sell':
                    trade_type = TradeType.SELL
                else:
                    log.warning(f'Unknown OKX trade side: {side}')
                    continue
                
                # Create trade object
                trade = Trade(
                    timestamp=timestamp,
                    location=location,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    trade_type=trade_type,
                    amount=amount,
                    rate=price,
                    fee=Fee(fee_amount) if fee_amount > ZERO else None,
                    fee_currency=fee_asset if fee_amount > ZERO else None,
                    link=entry.get('ordId', ''),
                )
                
                trades.append(trade)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize OKX trade',
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
        
        OKX deposit format:
        {
            'ccy': 'BTC',
            'amt': '0.001',
            'fee': '0',
            'ts': '1234567890123',
            'depId': '123456',
            'state': '2'  # 2 = success
        }
        
        OKX withdrawal format:
        {
            'ccy': 'BTC',
            'amt': '0.001',
            'fee': '0.0001',
            'ts': '1234567890123',
            'wdId': '123456',
            'state': '2'  # 2 = success
        }
        """
        movements = []
        
        # Process deposits
        for entry in deposits:
            try:
                # Only process successful deposits (state = 2)
                if entry.get('state') != '2':
                    continue
                    
                # Convert asset
                try:
                    asset = asset_from_okx(entry.get('ccy', ''))
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping OKX deposit with unknown asset',
                        deposit=entry,
                        error=str(e),
                    )
                    continue
                
                # Parse amounts
                amount = deserialize_asset_amount(entry.get('amt', '0'))
                fee = deserialize_fee(entry.get('fee', '0'))
                
                # Parse timestamp (milliseconds)
                timestamp = deserialize_timestamp_from_intms(entry.get('ts', 0))
                
                movement = AssetMovement(
                    timestamp=timestamp,
                    location=location,
                    category=AssetMovementCategory.DEPOSIT,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=Fee(fee) if fee > ZERO else Fee(ZERO),
                    link=entry.get('depId', ''),
                )
                
                movements.append(movement)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize OKX deposit',
                    deposit=entry,
                    error=str(e),
                )
                continue
        
        # Process withdrawals
        for entry in withdrawals:
            try:
                # Only process successful withdrawals (state = 2)
                if entry.get('state') != '2':
                    continue
                    
                # Convert asset
                try:
                    asset = asset_from_okx(entry.get('ccy', ''))
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping OKX withdrawal with unknown asset',
                        withdrawal=entry,
                        error=str(e),
                    )
                    continue
                
                # Parse amounts
                amount = deserialize_asset_amount(entry.get('amt', '0'))
                fee = deserialize_fee(entry.get('fee', '0'))
                
                # Parse timestamp (milliseconds)
                timestamp = deserialize_timestamp_from_intms(entry.get('ts', 0))
                
                movement = AssetMovement(
                    timestamp=timestamp,
                    location=location,
                    category=AssetMovementCategory.WITHDRAWAL,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=Fee(fee) if fee > ZERO else Fee(ZERO),
                    link=entry.get('wdId', ''),
                )
                
                movements.append(movement)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize OKX withdrawal',
                    withdrawal=entry,
                    error=str(e),
                )
                continue
                
        return movements
    
    def map_asset(self, exchange_symbol: str) -> Asset | None:
        """Map OKX asset symbol to Rotki Asset.
        
        Returns None if the asset cannot be mapped.
        """
        try:
            return asset_from_okx(exchange_symbol)
        except (UnknownAsset, UnsupportedAsset):
            return None