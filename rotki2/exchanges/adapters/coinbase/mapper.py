"""Coinbase data mapper adapter implementation."""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from rotki2.assets.base import Asset
from rotki2.assets.converters import asset_from_coinbase
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


class CoinbaseDataMapper(ExchangeDataMapperPort):
    """Coinbase data mapper adapter.
    
    Transforms raw Coinbase API responses into Rotki domain models.
    """
    
    def to_balances(self, raw_data: list[dict[str, Any]]) -> dict[Asset, AssetAmount]:
        """Transform raw balance data into Rotki balance format.
        
        Coinbase balance format:
        {
            'currency': 'BTC',
            'balance': '0.1',
            'available': '0.09',
            'hold': '0.01'
        }
        """
        balances: dict[Asset, AssetAmount] = {}
        
        for entry in raw_data:
            try:
                # Get currency
                currency = entry.get('currency', '')
                if not currency:
                    continue
                    
                # Convert to Rotki asset
                try:
                    asset = asset_from_coinbase(currency)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Coinbase balance for unknown asset {currency}',
                        error=str(e),
                    )
                    continue
                
                # Parse balance (total balance including holds)
                balance = deserialize_asset_amount(entry.get('balance', '0'))
                
                if balance > ZERO:
                    balances[asset] = balance
                    
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Coinbase balance entry',
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
        """Transform raw fill data into Rotki Trade objects.
        
        Coinbase fill format:
        {
            'trade_id': 123456,
            'product_id': 'BTC-USD',
            'price': '50000.00',
            'size': '0.001',
            'order_id': 'abc-123',
            'created_at': '2021-01-01T00:00:00.000000Z',
            'liquidity': 'T',
            'fee': '0.25',
            'settled': true,
            'side': 'buy',
            'user_id': 'xxx'
        }
        """
        trades = []
        
        for entry in raw_data:
            try:
                # Parse product ID (e.g., 'BTC-USD')
                product_id = entry.get('product_id', '')
                parts = product_id.split('-')
                if len(parts) != 2:
                    log.warning(f'Invalid Coinbase product ID: {product_id}')
                    continue
                    
                base_str, quote_str = parts
                
                # Convert assets
                try:
                    base_asset = asset_from_coinbase(base_str)
                    quote_asset = asset_from_coinbase(quote_str)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Coinbase trade with unknown asset',
                        trade=entry,
                        error=str(e),
                    )
                    continue
                
                # Parse amounts
                amount = deserialize_asset_amount(entry.get('size', '0'))
                price = deserialize_price(entry.get('price', '0'))
                fee_amount = deserialize_fee(entry.get('fee', '0'))
                
                # Parse timestamp
                created_at = entry.get('created_at', '')
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    timestamp = Timestamp(int(dt.timestamp()))
                except ValueError:
                    log.warning(f'Invalid Coinbase timestamp: {created_at}')
                    continue
                
                # Determine trade type
                side = entry.get('side', '').lower()
                if side == 'buy':
                    trade_type = TradeType.BUY
                    fee_currency = quote_asset  # Fee in quote currency for buys
                elif side == 'sell':
                    trade_type = TradeType.SELL
                    fee_currency = quote_asset  # Fee in quote currency for sells
                else:
                    log.warning(f'Unknown Coinbase trade side: {side}')
                    continue
                
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
                    link=str(entry.get('trade_id', '')),
                )
                
                trades.append(trade)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Coinbase trade',
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
        """Transform raw transfer data into AssetMovement objects.
        
        Coinbase transfer format:
        {
            'id': 'abc-123',
            'type': 'deposit' or 'withdraw',
            'created_at': '2021-01-01T00:00:00Z',
            'completed_at': '2021-01-01T01:00:00Z',
            'amount': '0.1',
            'currency': 'BTC',
            'details': {
                'crypto_address': '1A1zP1...',
                'crypto_transaction_hash': 'abc123...',
                'fee': '0.0001'
            }
        }
        """
        movements = []
        
        # Process deposits
        for entry in deposits:
            try:
                # Convert currency
                currency = entry.get('currency', '')
                try:
                    asset = asset_from_coinbase(currency)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Coinbase deposit with unknown asset {currency}',
                        error=str(e),
                    )
                    continue
                
                # Parse amount
                amount = deserialize_asset_amount(entry.get('amount', '0'))
                
                # Parse fee from details
                details = entry.get('details', {})
                fee = deserialize_fee(details.get('fee', '0'))
                
                # Parse timestamp
                completed_at = entry.get('completed_at', '')
                try:
                    dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                    timestamp = Timestamp(int(dt.timestamp()))
                except ValueError:
                    log.warning(f'Invalid Coinbase timestamp: {completed_at}')
                    continue
                
                movement = AssetMovement(
                    timestamp=timestamp,
                    location=location,
                    category=AssetMovementCategory.DEPOSIT,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=Fee(fee) if fee > ZERO else Fee(ZERO),
                    link=details.get('crypto_transaction_hash', entry.get('id', '')),
                )
                
                movements.append(movement)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Coinbase deposit',
                    deposit=entry,
                    error=str(e),
                )
                continue
        
        # Process withdrawals
        for entry in withdrawals:
            try:
                # Convert currency
                currency = entry.get('currency', '')
                try:
                    asset = asset_from_coinbase(currency)
                except (UnknownAsset, UnsupportedAsset) as e:
                    log.warning(
                        f'Skipping Coinbase withdrawal with unknown asset {currency}',
                        error=str(e),
                    )
                    continue
                
                # Parse amount
                amount = deserialize_asset_amount(entry.get('amount', '0'))
                
                # Parse fee from details
                details = entry.get('details', {})
                fee = deserialize_fee(details.get('fee', '0'))
                
                # Parse timestamp
                completed_at = entry.get('completed_at', '')
                try:
                    dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                    timestamp = Timestamp(int(dt.timestamp()))
                except ValueError:
                    log.warning(f'Invalid Coinbase timestamp: {completed_at}')
                    continue
                
                movement = AssetMovement(
                    timestamp=timestamp,
                    location=location,
                    category=AssetMovementCategory.WITHDRAWAL,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=Fee(fee) if fee > ZERO else Fee(ZERO),
                    link=details.get('crypto_transaction_hash', entry.get('id', '')),
                )
                
                movements.append(movement)
                
            except (ValueError, DeserializationError) as e:
                log.error(
                    'Failed to deserialize Coinbase withdrawal',
                    withdrawal=entry,
                    error=str(e),
                )
                continue
                
        return movements
    
    def map_asset(self, exchange_symbol: str) -> Asset | None:
        """Map Coinbase asset symbol to Rotki Asset."""
        try:
            return asset_from_coinbase(exchange_symbol)
        except (UnknownAsset, UnsupportedAsset):
            return None