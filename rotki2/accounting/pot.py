"""Async accounting pot for managing PnL calculations"""
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.cost_basis import CostBasisCalculator
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.errors.accounting import AccountingError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CostBasisMethod, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.events import EventsAccountant
    from rotkehlchen.accounting.pnl import PnlTotals
    from rotkehlchen.db.reports import DBAccountingReports
    from rotkehlchen.user_messages import MessagesAggregator
    from rotki2.accounting.price_historian import AsyncPriceHistorian
    from rotki2.api.v2.services.database import DatabaseService

logger = RotkehlchenLogsAdapter(__name__)


class AsyncAccountingPot:
    """Async version of AccountingPot for tracking cost basis and PnL
    
    This class manages the calculation of profit/loss for accounting events
    using async I/O for price lookups and database operations.
    """
    
    def __init__(
        self,
        database: 'DatabaseService',
        msg_aggregator: 'MessagesAggregator',
        price_historian: 'AsyncPriceHistorian',
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
        
        # Reset cost basis
        self.cost_basis.reset(settings)
    
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
        self.cost_basis.add_acquisition(
            event_type=event_type,
            asset=asset,
            amount=amount,
            rate=price,
            timestamp=timestamp,
            extra_data=extra_data,
        )
        
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
        spending_events = self.cost_basis.spend_asset(
            asset=asset,
            amount=amount,
            rate=price,
            timestamp=timestamp,
            event_type=event_type,
            extra_data=extra_data,
        )
        
        # Calculate PnL
        total_taxable_pnl = Balance()
        total_free_pnl = Balance()
        taxable_amount = ZERO
        free_amount = ZERO
        
        for acquisition_event, used_amount in spending_events:
            # Calculate gain/loss
            acquisition_rate = acquisition_event.rate
            gain_loss = (price - acquisition_rate) * used_amount
            gain_loss_in_profit_currency = gain_loss
            
            if taxable:
                taxable_amount += used_amount
                total_taxable_pnl += Balance(
                    amount=gain_loss,
                    usd_value=gain_loss_in_profit_currency,
                )
            else:
                free_amount += used_amount
                total_free_pnl += Balance(
                    amount=gain_loss,
                    usd_value=gain_loss_in_profit_currency,
                )
        
        # Track the PnL
        if taxable:
            self.taxable_pnl[event_type] += total_taxable_pnl
        else:
            self.free_pnl[event_type] += total_free_pnl
        
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
            self.cost_basis.add_acquisition(
                event_type=event_type,
                asset=asset,
                amount=amount,
                rate=price,
                timestamp=timestamp,
                extra_data=extra_data,
            )
        
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
        from rotkehlchen.accounting.pnl import PnlTotals
        
        return PnlTotals(
            totals=dict(self.pnl_totals),
            taxable=dict(self.taxable_pnl),
            free=dict(self.free_pnl),
        )
    
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