"""Async accounting pot for managing PnL calculations"""
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotki2.accounting.cost_basis.calculator import CostBasisCalculator
from rotkehlchen.accounting.structures.balance import Balance
from rotki2.accounting.structures import ProcessedAccountingEvent
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.errors.accounting import AccountingError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CostBasisMethod, Location, Price, Timestamp
from rotki2.accounting.pnl import PNL

if TYPE_CHECKING:
    from rotkehlchen.accounting.events import EventsAccountant
    from rotki2.accounting.pnl import PnlTotals
    from rotkehlchen.db.reports import DBAccountingReports
    from rotkehlchen.user_messages import MessagesAggregator
    from rotki2.accounting.price_historian import PriceHistorian
    from rotki2.api.v2.services.database import DatabaseService

logger = RotkehlchenLogsAdapter(__name__)


class AccountingPot:
    """Async version of AccountingPot for tracking cost basis and PnL
    
    This class manages the calculation of profit/loss for accounting events
    using async I/O for price lookups and database operations.
    """
    
    def __init__(
        self,
        database: 'DatabaseService',
        msg_aggregator: 'MessagesAggregator',
        price_historian: 'PriceHistorian',
        profit_currency: Asset,
        cost_basis_method: CostBasisMethod,
        ignored_action_ids: set[str] | None = None,
    ):
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.price_historian = price_historian
        self.profit_currency = profit_currency
        self.cost_basis_method = cost_basis_method
        self.ignored_action_ids = ignored_action_ids or set()
        
        # Cost basis calculator
        self.cost_basis = CostBasisCalculator(
            database=database,
            msg_aggregator=msg_aggregator,
        )
        
        # PnL tracking
        self.pnl_totals = defaultdict(lambda: Balance())
        self.free_pnl = defaultdict(lambda: Balance())
        self.taxable_pnl = defaultdict(lambda: Balance())
        
        # Event tracking
        self.processed_events: list[ProcessedAccountingEvent] = []
        self.processed_actions_count = 0
        
        # Settings
        self.settings: dict[str, Any] = {}
        self.start_ts: Timestamp = Timestamp(0)
        self.end_ts: Timestamp = Timestamp(0)
        self.report_id: int | None = None
        
        # Events accountant for rule-based processing
        self.events_accountant: EventsAccountant | None = None
        
    def reset(
        self,
        settings: dict[str, Any],
        start_ts: Timestamp,
        end_ts: Timestamp,
        report_id: int,
    ) -> None:
        """Reset the pot for a new accounting period"""
        self.settings = settings
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.report_id = report_id
        
        # Clear tracking data
        self.pnl_totals.clear()
        self.free_pnl.clear()
        self.taxable_pnl.clear()
        self.processed_events.clear()
        self.processed_actions_count = 0
        
        # Reset cost basis with DBSettings object
        from rotkehlchen.db.settings import DBSettings
        db_settings = DBSettings(
            main_currency=self.profit_currency,
            cost_basis_method=self.cost_basis_method,
            **settings
        )
        self.cost_basis.reset(db_settings)
    
    async def add_in_event(
        self,
        event_type: ActionType,
        asset: Asset,
        amount: FVal,
        timestamp: Timestamp,
        price: Price | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> tuple[FVal, FVal]:
        """Add an incoming asset event (acquisition)
        
        Returns (taxable_amount, free_amount)
        """
        if price is None:
            price = await self.get_rate_in_profit_currency(asset, timestamp)
        
        # Calculate value in profit currency
        value_in_profit_currency = price * amount
        
        # Add to cost basis
        # Create a processed event for the acquisition
        event = ProcessedAccountingEvent(
            event_type=event_type,
            notes=f'Acquisition of {amount} {asset.identifier}',
            location=extra_data.get('location', Location.EXTERNAL) if extra_data else Location.EXTERNAL,
            timestamp=timestamp,
            asset=asset,
            free_amount=ZERO,
            taxable_amount=amount,
            price=price,
            pnl=PNL(),
            cost_basis=None,
            index=self.processed_actions_count,
            extra_data=extra_data or {},
        )
        self.cost_basis.obtain_asset(event)
        
        # Track the acquisition
        self._add_to_pnl_totals(
            event_type=event_type,
            asset=asset,
            amount=amount,
            value=value_in_profit_currency,
            is_taxable=True,
        )
        
        return amount, ZERO
    
    async def add_out_event(
        self,
        event_type: ActionType,
        asset: Asset,
        amount: FVal,
        timestamp: Timestamp,
        price: Price | None = None,
        taxable: bool = True,
        extra_data: dict[str, Any] | None = None,
    ) -> tuple[FVal, FVal]:
        """Add an outgoing asset event (spend/sale)
        
        Returns (taxable_amount, free_amount)
        """
        if price is None:
            price = await self.get_rate_in_profit_currency(asset, timestamp)
        
        # Get cost basis for the spend
        location = extra_data.get('location', Location.EXTERNAL) if extra_data else Location.EXTERNAL
        originating_event_id = extra_data.get('event_id') if extra_data else None
        
        cost_basis_info = await self.cost_basis.spend_asset(
            originating_event_id=originating_event_id,
            location=location,
            timestamp=timestamp,
            asset=asset,
            amount=amount,
            rate=price,
            taxable_spend=taxable,
        )
        
        # Calculate PnL based on cost basis info
        if taxable and cost_basis_info:
            taxable_amount = cost_basis_info.taxable_amount
            free_amount = amount - taxable_amount
            # The PnL calculation is handled by the cost basis calculator
        else:
            taxable_amount = ZERO if not taxable else amount
            free_amount = amount if not taxable else ZERO
        
        # Track the spend event - PnL calculation will happen later
        # when processing the event
        
        # Track the spend
        value_in_profit_currency = price * amount
        self._add_to_pnl_totals(
            event_type=event_type,
            asset=asset,
            amount=-amount,  # Negative for outgoing
            value=value_in_profit_currency,
            is_taxable=taxable,
        )
        
        return taxable_amount, free_amount
    
    async def add_asset_change_event(
        self,
        event_type: ActionType,
        asset: Asset,
        amount: FVal,
        timestamp: Timestamp,
        price: Price | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> None:
        """Add an event that changes asset amount without acquisition/disposal
        
        Examples: interest, rewards, fees
        """
        if price is None:
            price = await self.get_rate_in_profit_currency(asset, timestamp)
        
        value_in_profit_currency = price * amount
        
        # For positive amounts (income), add to cost basis at current price
        if amount > ZERO:
            # Create a processed event for the acquisition
            event = ProcessedAccountingEvent(
                event_type=event_type,
                notes=f'Asset change: {amount} {asset.identifier}',
                location=extra_data.get('location', Location.EXTERNAL) if extra_data else Location.EXTERNAL,
                timestamp=timestamp,
                asset=asset,
                free_amount=ZERO,
                taxable_amount=amount,
                price=price,
                pnl=PNL(),
                cost_basis=None,
                index=self.processed_actions_count,
                extra_data=extra_data or {},
            )
            self.cost_basis.obtain_asset(event)
        
        # Track the change
        self._add_to_pnl_totals(
            event_type=event_type,
            asset=asset,
            amount=amount,
            value=value_in_profit_currency,
            is_taxable=True,
        )
    
    async def get_rate_in_profit_currency(
        self,
        asset: Asset,
        timestamp: Timestamp,
    ) -> Price:
        """Get the rate of an asset in profit currency at given timestamp"""
        if asset == self.profit_currency:
            return Price(ONE)
        
        try:
            price = await self.price_historian.query_historical_price(
                from_asset=asset,
                to_asset=self.profit_currency,
                timestamp=timestamp,
            )
            return price
        except (NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset) as e:
            # Log the error and re-raise
            logger.error(
                f'Failed to get price for {asset.identifier} '
                f'at {timestamp}: {str(e)}'
            )
            raise
    
    def _add_to_pnl_totals(
        self,
        event_type: ActionType,
        asset: Asset,
        amount: FVal,
        value: FVal,
        is_taxable: bool,
    ) -> None:
        """Add amounts to PnL totals tracking"""
        balance = Balance(amount=amount, usd_value=value)
        self.pnl_totals[event_type] += balance
        
        if is_taxable:
            self.taxable_pnl[event_type] += balance
        else:
            self.free_pnl[event_type] += balance
    
    def add_processed_event(
        self,
        event: ProcessedAccountingEvent,
    ) -> None:
        """Add a processed event to the list"""
        self.processed_events.append(event)
        self.processed_actions_count += 1
        
        # Flush to database periodically
        if len(self.processed_events) >= 100:
            # This will be called from the accountant
            pass
    
    async def flush_processed_events(self) -> None:
        """Flush processed events to database"""
        if not self.processed_events or not self.report_id:
            return
        
        dbpnl = DBAccountingReports(self.database)
        await dbpnl.add_report_data(
            report_id=self.report_id,
            events=self.processed_events,
        )
        
        self.processed_events.clear()
    
    def get_pnl_totals(self) -> 'PnlTotals':
        """Get the PnL totals for all event types"""
        from rotki2.accounting.pnl import PnlTotals
        
        return PnlTotals(
            totals=dict(self.pnl_totals),
            taxable=dict(self.taxable_pnl),
            free=dict(self.free_pnl),
        )
    
    async def get_prices_for_swap(
            self,
            timestamp: Timestamp,
            amount_in: FVal,
            asset_in: Asset,
            amount_out: FVal,
            asset_out: Asset,
            fee_info: tuple[FVal, Asset] | None,
    ) -> tuple[Price, Price] | None:
        """
        Calculates the prices for assets going in and out of a swap/trade.

        The algorithm is:
        1. Query oracles for prices of asset_out and asset_in.
        2.1 If either of the assets is fiat -- use its amount and price for calculations.
        2.2. If neither of the assets is fiat -- use `out_price` if `out_price` is known,
        otherwise `in_price`.
        3.1 If `fee_info` is provided and it's included in the cost basis,
        fee is included in the price of one of the assets.
        3.2. If `asset_out` is fiat -- fee is added to `calculated_in_price`.
        3.3. If `asset_in` is fiat -- fee is subtracted from `calculated_out_price`.
        3.4. Otherwise fee is added to the price of the asset that was bought.

        Returns (calculated_out_price, calculated_in_price) or None if it can't find proper prices.
        """
        if ZERO in (amount_in, amount_out):
            logger.error(
                f'At get_prices_for_swap got a zero amount. {asset_in=} {amount_in=} '
                f'{asset_out=} {amount_out=}. Skipping ...')
            return None

        # Get prices from oracles
        try:
            out_price = await self.get_rate_in_profit_currency(asset_out, timestamp)
        except (NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset):
            out_price = None
            
        try:
            in_price = await self.get_rate_in_profit_currency(asset_in, timestamp)
        except (NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset):
            in_price = None

        # Calculate base prices
        if asset_out.is_fiat():
            calculated_out_price = out_price or Price(ONE)
            calculated_in_price = Price(amount_out / amount_in)
        elif asset_in.is_fiat():
            calculated_in_price = in_price or Price(ONE)
            calculated_out_price = Price(amount_in / amount_out)
        else:
            # Neither is fiat, use oracle prices
            if out_price is not None:
                calculated_out_price = out_price
                calculated_in_price = Price(amount_out * out_price / amount_in)
            elif in_price is not None:
                calculated_in_price = in_price
                calculated_out_price = Price(amount_in * in_price / amount_out)
            else:
                # No prices available
                return None

        # Handle fees if provided
        if fee_info and self.settings.get('include_fees_in_cost_basis', True):
            fee_amount, fee_asset = fee_info
            if fee_amount > ZERO:
                try:
                    fee_price = await self.get_rate_in_profit_currency(fee_asset, timestamp)
                    fee_value = fee_amount * fee_price
                    
                    if asset_out.is_fiat():
                        # Add fee to in price
                        calculated_in_price = Price(
                            (calculated_in_price * amount_in + fee_value) / amount_in
                        )
                    elif asset_in.is_fiat():
                        # Subtract fee from out price
                        calculated_out_price = Price(
                            (calculated_out_price * amount_out - fee_value) / amount_out
                        )
                    else:
                        # Add fee to the bought asset (out)
                        calculated_out_price = Price(
                            (calculated_out_price * amount_out + fee_value) / amount_out
                        )
                except (NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset):
                    # Couldn't get fee price, continue without it
                    pass

        return calculated_out_price, calculated_in_price
    
    def to_dict(self) -> dict[str, Any]:
        """Convert pot state to dictionary"""
        return {
            'profit_currency': self.profit_currency.identifier,
            'cost_basis_method': self.cost_basis_method.value,
            'processed_actions': self.processed_actions_count,
            'pnl_totals': {
                k.value: {'amount': str(v.amount), 'usd_value': str(v.usd_value)}
                for k, v in self.pnl_totals.items()
            },
        }