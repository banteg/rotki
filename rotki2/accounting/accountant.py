"""Async accountant for processing history events and calculating PnL"""
import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import anyio

from rotkehlchen.accounting.events import EventsAccountant
from rotkehlchen.accounting.structures.balance import Balance
from rotki2.accounting.structures import ProcessedAccountingEvent
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.limits import FREE_PNL_EVENTS_LIMIT
from rotkehlchen.errors.accounting import AccountingError
from rotkehlchen.errors.misc import DBUpgradeError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now
from rotki2.accounting.aggregator import EVMAccountingAggregator
from rotki2.accounting.pot import AccountingPot
from rotki2.accounting.price_historian import PriceHistorian

if TYPE_CHECKING:
    from collections.abc import Iterator
    
    from rotki2.accounting.mixins import AccountingEventMixin
    from rotkehlchen.accounting.structures.types import ActionType
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.reports import DBAccountingReports
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.user_messages import MessagesAggregator
    from rotki2.api.v2.services.database import DatabaseService

logger = RotkehlchenLogsAdapter(__name__)


class Accountant:
    """Async version of the Accountant for processing accounting events
    
    This class orchestrates the processing of historical trading events
    and calculates profit/loss using async I/O operations.
    """
    
    def __init__(
        self,
        db: 'DatabaseService',
        msg_aggregator: 'MessagesAggregator',
        chains_aggregator: 'ChainsAggregator',
        premium: 'Premium | None',
        price_historian: 'PriceHistorian | None' = None,
    ):
        self.db = db
        self.msg_aggregator = msg_aggregator
        self.chains_aggregator = chains_aggregator
        self.premium = premium
        self.price_historian = price_historian or PriceHistorian()
        
        # Accounting components
        self.pots: list[AccountingPot] = []
        self.csv_exporter = None  # Will be initialized per report
        
        # Caches
        self.processable_events_cache: dict[str, bool] = {}
        self.ignored_asset_ids: set[str] | None = None
        
        # Processing state
        self._processing = False
        self._current_report_id: int | None = None
        
    async def process_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        history_events: Iterator['AccountingEventMixin'],
    ) -> int:
        """Process history events and generate PnL report
        
        This is the async version of the main processing method.
        Returns the report ID.
        """
        if self._processing:
            raise AccountingError('Accounting already in progress')
            
        self._processing = True
        report_id = -1
        
        try:
            # Initialize processing
            report_id = await self._initialize_processing(start_ts, end_ts)
            self._current_report_id = report_id
            
            # Process events
            await self._process_events(history_events)
            
            # Finalize report
            await self._finalize_report(report_id)
            
            return report_id
            
        except Exception as e:
            logger.error(f'Error during accounting: {str(e)}')
            if report_id != -1:
                await self._mark_report_failed(report_id)
            raise
        finally:
            self._processing = False
            self._current_report_id = None
            self._cleanup()
    
    async def _initialize_processing(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> int:
        """Initialize accounting processing
        
        Sets up the accounting pot, loads settings, and creates report.
        """
        # Get settings and ignored assets
        settings = await self.db.get_settings()
        self.ignored_asset_ids = await self.db.get_ignored_asset_ids()
        ignored_action_ids = await self.db.get_ignored_action_ids()
        
        # Create report in database
        dbpnl = DBAccountingReports(self.db)
        report_id = await dbpnl.add_report(
            first_processed_timestamp=start_ts,
            last_processed_timestamp=end_ts,
        )
        
        # Initialize accounting pot
        pot = AccountingPot(
            database=self.db,
            msg_aggregator=self.msg_aggregator,
            price_historian=self.price_historian,
            profit_currency=settings.main_currency,
            cost_basis_method=settings.cost_basis_method,
            ignored_action_ids=ignored_action_ids,
        )
        
        # Initialize pot components
        pot.reset(
            settings=settings.to_dict(),
            start_ts=start_ts,
            end_ts=end_ts,
            report_id=report_id,
        )
        
        self.pots = [pot]
        
        # Initialize CSV exporter if needed
        if settings.csv_export_enabled:
            # CSV exporter initialization would go here
            pass
            
        return report_id
    
    async def _process_events(
        self,
        history_events: Iterator['AccountingEventMixin'],
    ) -> None:
        """Process all history events"""
        # Convert to peekable iterator
        from more_itertools import peekable
        events_iterator = peekable(history_events)
        
        events_processed = 0
        last_flush_timestamp = 0
        
        # Get EVM accounting aggregators
        evm_aggregators = await self._get_evm_aggregators()
        
        while True:
            try:
                event = next(events_iterator)
            except StopIteration:
                break
                
            # Process the event
            try:
                await self._process_event(
                    event=event,
                    events_iterator=events_iterator,
                    evm_aggregators=evm_aggregators,
                )
                events_processed += 1
                
            except PriceQueryUnsupportedAsset as e:
                logger.warning(f'Skipping event due to unsupported asset: {e}')
                self.msg_aggregator.add_warning(str(e))
                continue
                
            except NoPriceForGivenTimestamp as e:
                logger.warning(f'Skipping event due to missing price: {e}')
                self.msg_aggregator.add_warning(str(e))
                continue
                
            except RemoteError as e:
                logger.error(f'Skipping event due to remote error: {e}')
                self.msg_aggregator.add_error(str(e))
                continue
                
            except AccountingError as e:
                logger.error(f'Skipping event due to accounting error: {e}')
                self.msg_aggregator.add_error(str(e))
                continue
            
            # Check premium limits
            if self.premium is None and events_processed >= FREE_PNL_EVENTS_LIMIT:
                self.msg_aggregator.add_warning(
                    f'Free plan limit of {FREE_PNL_EVENTS_LIMIT} events reached'
                )
                break
            
            # Yield control periodically
            if events_processed % 500 == 0:
                # Flush processed events to database
                await self._flush_processed_events()
                await anyio.sleep(0.5)
    
    async def _process_event(
        self,
        event: 'AccountingEventMixin',
        events_iterator: Any,  # peekable iterator
        evm_aggregators: 'EVMAccountingAggregator',
    ) -> None:
        """Process a single accounting event"""
        # Check if event should be ignored
        if self._should_ignore_event(event):
            return
            
        # Process through accounting pot
        pot = self.pots[0]  # Currently using single pot
        
        # Special handling for EVM events
        if hasattr(event, 'counterparty') and event.counterparty:
            await evm_aggregators.process_event(
                pot=pot,
                event=event,
                events_iterator=events_iterator,
            )
        else:
            # Regular event processing
            await event.process(
                accounting=pot,
                events_iterator=events_iterator,
            )
    
    def _should_ignore_event(self, event: 'AccountingEventMixin') -> bool:
        """Check if event should be ignored"""
        # Check ignored assets
        if hasattr(event, 'asset') and self.ignored_asset_ids:
            if event.asset.identifier in self.ignored_asset_ids:
                return True
                
        # Check processable cache
        event_key = self._get_event_cache_key(event)
        if event_key in self.processable_events_cache:
            return not self.processable_events_cache[event_key]
            
        # Default to processing
        return False
    
    def _get_event_cache_key(self, event: 'AccountingEventMixin') -> str:
        """Generate cache key for event processability"""
        if isinstance(event, HistoryEvent):
            return f"{event.event_type}_{event.event_subtype}_{event.counterparty}"
        return f"{type(event).__name__}"
    
    async def _get_evm_aggregators(self) -> 'EVMAccountingAggregator':
        """Get EVM accounting aggregators"""
        return EVMAccountingAggregator(
            database=self.db,
            msg_aggregator=self.msg_aggregator,
            chains_aggregator=self.chains_aggregator,
            premium=self.premium,
        )
    
    async def _flush_processed_events(self) -> None:
        """Flush processed events to database"""
        for pot in self.pots:
            await pot.flush_processed_events()
    
    async def _finalize_report(self, report_id: int) -> None:
        """Finalize the accounting report"""
        # Flush any remaining events
        await self._flush_processed_events()
        
        # Get PnL totals from pot
        pot = self.pots[0]
        pnl_totals = pot.get_pnl_totals()
        
        # Save report overview
        dbpnl = DBAccountingReports(self.db)
        await dbpnl.add_report_overview(
            report_id=report_id,
            pnl_totals=pnl_totals,
            processed_actions=pot.processed_actions_count,
            total_actions=pot.processed_actions_count,  # In async version, we process all
        )
        
        # Export CSV if enabled
        if self.csv_exporter:
            await self._export_csv(report_id)
    
    async def _mark_report_failed(self, report_id: int) -> None:
        """Mark a report as failed"""
        try:
            dbpnl = DBAccountingReports(self.db)
            await dbpnl.mark_report_failed(report_id)
        except Exception as e:
            logger.error(f'Failed to mark report as failed: {e}')
    
    async def _export_csv(self, report_id: int) -> None:
        """Export report to CSV"""
        # CSV export logic would go here
        pass
    
    def _cleanup(self) -> None:
        """Clean up after processing"""
        # Clear caches
        self.processable_events_cache.clear()
        self.ignored_asset_ids = None
        
        # Reset pots
        for pot in self.pots:
            pot.reset()
        self.pots.clear()
    
    def activate_premium_status(self, premium: 'Premium') -> None:
        """Activate premium features"""
        self.premium = premium
    
    def deactivate_premium_status(self) -> None:
        """Deactivate premium features"""
        self.premium = None