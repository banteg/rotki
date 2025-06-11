"""Accounting module using ORM for database operations"""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import gevent
from more_itertools import peekable

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT
from rotkehlchen.accounting.export.csv import CSVExporter
from rotkehlchen.accounting.pot import AccountingPot
from rotkehlchen.accounting.types import EventAccountingRuleStatus, MissingPrice
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair, UnsupportedAsset
from rotkehlchen.errors.misc import AccountingError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import EVM_CHAIN_IDS_WITH_TRANSACTIONS, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.data_structures import DefaultLRUCache, LRUCacheWithRemove

if TYPE_CHECKING:
    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.orm.database import RotkehlchenDatabase


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# size assumes a user loads 5 pages of 100 events each one
# and each event having in average 3 subevents.
# TODO: Make this changeable depending on user's set page size
PROCESSABLE_EVENTS_CACHE_SIZE = 1500


class Accountant:
    """Accountant class using ORM for database operations"""

    def __init__(
            self,
            db: 'RotkehlchenDatabase',
            msg_aggregator: MessagesAggregator,
            chains_aggregator: 'ChainsAggregator',
            premium: Premium | None,
    ) -> None:
        self.db = db
        self.msg_aggregator = msg_aggregator
        self.csvexporter = CSVExporter(database=db)
        evm_accounting_aggregators = EVMAccountingAggregators([chains_aggregator.get_evm_manager(x).accounting_aggregator for x in EVM_CHAIN_IDS_WITH_TRANSACTIONS])

        # TODO: Allow for setting of multiple accounting pots
        self.pots = [
            AccountingPot(
                database=db,
                evm_accounting_aggregators=evm_accounting_aggregators,
                msg_aggregator=msg_aggregator,
                is_dummy_pot=False,
            ),
        ]

        self.currently_processing_timestamp = Timestamp(-1)
        self.first_processed_timestamp = Timestamp(-1)
        self.premium = premium
        # cache to know what events will be processed or not during accounting
        self.processable_events_cache: LRUCacheWithRemove[int, EventAccountingRuleStatus] = LRUCacheWithRemove(maxsize=PROCESSABLE_EVENTS_CACHE_SIZE)
        # map event rules signatures to a list of event identifiers affected by them
        # used to know which events need to be invalidated when updating a rule
        self.processable_events_cache_signatures: DefaultLRUCache[int, list[int]] = DefaultLRUCache(default_factory=list, maxsize=PROCESSABLE_EVENTS_CACHE_SIZE)
        self.ignored_asset_ids: set[str] = set()  # populated in process_history so that we load them in memory once during accounting and not reload them from the DB for every single event processing

    def activate_premium_status(self, premium: Premium) -> None:
        self.premium = premium

    def deactivate_premium_status(self) -> None:
        self.premium = None

    @property
    def query_start_ts(self) -> Timestamp:
        return self.pots[0].query_start_ts

    @property
    def query_end_ts(self) -> Timestamp:
        return self.pots[0].query_end_ts

    def _process_skipping_exception(
            self,
            exception: Exception,
            events: Sequence['AccountingEventMixin'],
            count: int,
            reason: str,
    ) -> int:
        event = events[count]
        ts = event.get_timestamp()
        identifier = event.get_identifier()
        self.msg_aggregator.add_error(
            f'Skipping event with id {identifier} at '
            f'{ts} during history processing due to {reason}: {exception!s}',
        )
        log.error(
            f'Skipping event with id {identifier} at {ts} '
            f'during history processing due to {reason}',
            exc_info=exception,
        )
        return count + 1

    def process_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            report_id: int,
    ) -> tuple[list[MissingPrice], int]:
        """Process history events for accounting using ORM
        
        Returns a tuple of missing prices and processed events count
        """
        log.info(
            f'Started processing history from {start_ts} to {end_ts} with report id {report_id}',
        )
        
        # Load ignored assets into memory using ORM
        self._load_ignored_assets_orm()
        
        # Create report entry using ORM
        self._create_report_entry_orm(report_id, start_ts, end_ts)
        
        missing_prices: list[MissingPrice] = []
        events_processed = 0
        
        # Get events from database using ORM
        events = self._get_accounting_events_orm(start_ts, end_ts)
        
        events_iterator = peekable(events)
        count = 0
        
        for pot in self.pots:
            pot.reset(
                settings=self._get_accounting_settings_orm(),
                start_ts=start_ts,
                end_ts=end_ts,
                report_id=report_id,
            )
        
        while True:
            if count >= len(events):
                break
                
            event = events[count]
            
            # Check if event should be skipped based on rules
            if self._should_skip_event_orm(event):
                count += 1
                continue
            
            self.currently_processing_timestamp = event.get_timestamp()
            self.first_processed_timestamp = min(
                self.first_processed_timestamp,
                self.currently_processing_timestamp,
            ) if self.first_processed_timestamp != Timestamp(-1) else self.currently_processing_timestamp
            
            try:
                for pot in self.pots:
                    pot.process_event(event)
                events_processed += 1
            except (UnknownAsset, UnprocessableTradePair, UnsupportedAsset) as e:
                count = self._process_skipping_exception(
                    exception=e,
                    events=events,
                    count=count,
                    reason='asset/pair error',
                )
                continue
            except (NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset) as e:
                missing_prices.append(MissingPrice(
                    asset=event.get_assets(),
                    timestamp=event.get_timestamp(),
                    error=str(e),
                ))
                count = self._process_skipping_exception(
                    exception=e,
                    events=events,
                    count=count,
                    reason='price error',
                )
                continue
            except AccountingError as e:
                count = self._process_skipping_exception(
                    exception=e,
                    events=events,
                    count=count,
                    reason='accounting error',
                )
                continue
            except RemoteError as e:
                count = self._process_skipping_exception(
                    exception=e,
                    events=events,
                    count=count,
                    reason='remote error',
                )
                continue
            
            count += 1
        
        # Save final state using ORM
        self._save_accounting_state_orm(report_id)
        
        log.info(
            f'Finished processing history from {start_ts} to {end_ts}. '
            f'Processed {events_processed} events',
        )
        
        return missing_prices, events_processed

    def _load_ignored_assets_orm(self) -> None:
        """Load ignored assets using ORM"""
        ignored_assets = self.db.repos.ignored_assets.get_all_ignored_assets()
        self.ignored_asset_ids = {asset.identifier for asset in ignored_assets}

    def _create_report_entry_orm(
            self,
            report_id: int,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Create accounting report entry using ORM"""
        with self.db.repos.unit_of_work():
            self.db.repos.accounting_reports.create_report(
                report_id=report_id,
                start_ts=start_ts,
                end_ts=end_ts,
            )

    def _get_accounting_events_orm(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list['AccountingEventMixin']:
        """Get accounting events from database using ORM"""
        # Get history events
        history_events = self.db.repos.history_events.get_events(
            from_timestamp=start_ts,
            to_timestamp=end_ts,
        )
        
        # Get trades
        trades = self.db.repos.trades.get_trades(
            from_timestamp=start_ts,
            to_timestamp=end_ts,
        )
        
        # TODO: Combine and sort all events by timestamp
        # TODO: Convert ORM models to AccountingEventMixin instances
        all_events = []
        
        return sorted(all_events, key=lambda x: x.get_timestamp())

    def _should_skip_event_orm(self, event: 'AccountingEventMixin') -> bool:
        """Check if event should be skipped based on accounting rules using ORM"""
        event_id = event.get_identifier()
        
        # Check cache first
        if event_id in self.processable_events_cache:
            return self.processable_events_cache[event_id] == EventAccountingRuleStatus.NOT_PROCESSED
        
        # Check database for rules
        # TODO: Implement rule checking using ORM
        # TODO: This would query accounting_rules repository
        
        return False

    def _get_accounting_settings_orm(self) -> DBSettings:
        """Get accounting settings using ORM"""
        settings_dict = self.db.repos.settings.get_all_settings()
        # TODO: Convert to DBSettings properly
        return DBSettings(**settings_dict)

    def _save_accounting_state_orm(self, report_id: int) -> None:
        """Save accounting state to database using ORM"""
        with self.db.repos.unit_of_work():
            # Save PnL data
            for pot in self.pots:
                # TODO: Save pot state to database
                # TODO: This would use pnl_reports repository
                pass

    def get_report(self, report_id: int) -> dict:
        """Get accounting report by ID using ORM"""
        report = self.db.repos.accounting_reports.get_report(report_id)
        if not report:
            raise ValueError(f"Report with id {report_id} not found")
        
        # TODO: Build complete report data structure
        return {
            'report_id': report.identifier,
            'start_ts': report.start_ts,
            'end_ts': report.end_ts,
            'first_processed_timestamp': report.first_processed_timestamp,
            'last_processed_timestamp': report.last_processed_timestamp,
            'processed_actions': report.processed_actions,
            'total_actions': report.total_actions,
            # TODO: Add PnL data, events, etc.
        }

    def delete_report(self, report_id: int) -> None:
        """Delete accounting report using ORM"""
        with self.db.repos.unit_of_work():
            self.db.repos.accounting_reports.delete_report(report_id)

    def export_report(
            self,
            report_id: int,
            directory_path: Path,
    ) -> tuple[bool, str]:
        """Export accounting report to CSV using ORM"""
        try:
            report = self.get_report(report_id)
            # TODO: Implement CSV export using report data
            # TODO: This would use the CSVExporter with ORM data
            
            return True, str(directory_path)
        except Exception as e:
            log.error(f"Failed to export report {report_id}: {e}")
            return False, str(e)

    def get_latest_report_id(self) -> int | None:
        """Get the latest report ID using ORM"""
        return self.db.repos.accounting_reports.get_latest_report_id()

    def get_all_reports(self) -> list[dict]:
        """Get all accounting reports using ORM"""
        reports = self.db.repos.accounting_reports.get_all_reports()
        return [
            {
                'report_id': report.identifier,
                'start_ts': report.start_ts,
                'end_ts': report.end_ts,
                'processed_actions': report.processed_actions,
                'total_actions': report.total_actions,
            }
            for report in reports
        ]

    def check_if_pnl_report_is_active(self, report_id: int) -> bool:
        """Check if a PnL report is currently being processed"""
        # TODO: Implement using ORM to check report status
        report = self.db.repos.accounting_reports.get_report(report_id)
        return report is not None and report.processed_actions < report.total_actions

    def get_pnl_for_report(
            self,
            report_id: int,
            event_type: str | None = None,
    ) -> dict:
        """Get PnL data for a specific report using ORM"""
        # TODO: Implement PnL data retrieval using ORM
        # TODO: This would query pnl_events repository with filters
        return {
            'events': [],
            'total_pnl': '0',
        }