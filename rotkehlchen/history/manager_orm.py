"""History management using ORM"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.orm.database import RotkehlchenDatabase
    from rotkehlchen.exchanges.manager import ExchangeManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HistoryQueryingManager:
    """Manages historical data queries using ORM"""

    def __init__(
            self,
            user_directory: Path,
            db: 'RotkehlchenDatabase',
            msg_aggregator: MessagesAggregator,
            exchange_manager: 'ExchangeManager',
            chains_aggregator: 'ChainsAggregator',
    ):
        self.user_directory = user_directory
        self.db = db
        self.msg_aggregator = msg_aggregator
        self.exchange_manager = exchange_manager
        self.chains_aggregator = chains_aggregator

    def get_history_events(
            self,
            filter_query: HistoryEventFilterQuery,
            has_premium: bool = True,
            group_by_event_ids: bool = False,
    ) -> tuple[list[HistoryEvent], int]:
        """Get history events from database using ORM
        
        Returns tuple of (events, total_count)
        """
        # Get events from repository with filters
        events = self.db.repos.history_events.get_events_with_filters(
            from_timestamp=filter_query.from_ts,
            to_timestamp=filter_query.to_ts,
            event_types=filter_query.event_types,
            event_subtypes=filter_query.event_subtypes,
            location=filter_query.location,
            location_labels=filter_query.location_labels,
            asset=filter_query.asset,
            limit=filter_query.limit,
            offset=filter_query.offset,
            order_by=filter_query.order_by_attributes,
            order_ascending=filter_query.ascending,
        )
        
        # Get total count for pagination
        total_count = self.db.repos.history_events.count_events_with_filters(
            from_timestamp=filter_query.from_ts,
            to_timestamp=filter_query.to_ts,
            event_types=filter_query.event_types,
            event_subtypes=filter_query.event_subtypes,
            location=filter_query.location,
            location_labels=filter_query.location_labels,
            asset=filter_query.asset,
        )
        
        # Convert ORM models to HistoryEvent objects
        history_events = []
        for event in events:
            # TODO: Properly convert ORM model to HistoryEvent
            # TODO: This needs proper implementation based on the model structure
            history_event = HistoryEvent(
                event_identifier=event.event_identifier,
                sequence_index=event.sequence_index,
                timestamp=Timestamp(event.timestamp),
                location=Location.deserialize_from_db(event.location),
                event_type=event.event_type,
                event_subtype=event.event_subtype,
                asset=Asset(event.asset),
                balance=Balance(amount=event.amount),
                # TODO: Add other fields
            )
            history_events.append(history_event)
        
        # Group by event IDs if requested
        if group_by_event_ids:
            grouped_events = self._group_events_by_id(history_events)
            return grouped_events, total_count
        
        return history_events, total_count

    def _group_events_by_id(self, events: list[HistoryEvent]) -> list[HistoryEvent]:
        """Group events by their event identifier"""
        grouped = defaultdict(list)
        
        for event in events:
            grouped[event.event_identifier].append(event)
        
        # Return the first event from each group
        result = []
        for event_group in grouped.values():
            # Sort by sequence index and take the first
            event_group.sort(key=lambda e: e.sequence_index)
            result.append(event_group[0])
        
        return result

    def add_history_events(self, events: list[HistoryEvent]) -> list[int]:
        """Add history events to database using ORM
        
        Returns list of identifiers for successfully added events
        """
        added_identifiers = []
        
        with self.db.repos.unit_of_work():
            for event in events:
                try:
                    # TODO: Convert HistoryEvent to ORM model
                    identifier = self.db.repos.history_events.add_event(event)
                    added_identifiers.append(identifier)
                except Exception as e:
                    log.error(f'Failed to add history event: {e}')
                    self.msg_aggregator.add_error(
                        f'Failed to add history event: {str(e)}'
                    )
        
        return added_identifiers

    def edit_history_events(self, events: list[HistoryEvent]) -> list[bool]:
        """Edit existing history events using ORM
        
        Returns list of success flags for each event
        """
        results = []
        
        with self.db.repos.unit_of_work():
            for event in events:
                try:
                    # TODO: Convert HistoryEvent to update parameters
                    success = self.db.repos.history_events.update_event(
                        identifier=event.identifier,
                        event=event,
                    )
                    results.append(success)
                except Exception as e:
                    log.error(f'Failed to edit history event {event.identifier}: {e}')
                    results.append(False)
        
        return results

    def delete_history_events(
            self,
            identifiers: list[int],
            force_delete: bool = False,
    ) -> list[bool]:
        """Delete history events from database using ORM
        
        Returns list of success flags for each deletion
        """
        results = []
        
        with self.db.repos.unit_of_work():
            for identifier in identifiers:
                try:
                    if force_delete:
                        # Force delete even if event is referenced
                        success = self.db.repos.history_events.force_delete_event(identifier)
                    else:
                        success = self.db.repos.history_events.delete_event(identifier)
                    results.append(success)
                except Exception as e:
                    log.error(f'Failed to delete history event {identifier}: {e}')
                    results.append(False)
        
        return results

    def get_history_events_count(
            self,
            from_timestamp: Timestamp | None = None,
            to_timestamp: Timestamp | None = None,
            location: Location | None = None,
    ) -> int:
        """Get count of history events using ORM"""
        return self.db.repos.history_events.count_events_with_filters(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            location=location.serialize_for_db() if location else None,
        )

    def query_balances(
            self,
            requested_save_data: bool = True,
            save_despite_errors: bool = False,
            timestamp: Timestamp | None = None,
            ignore_cache: bool = False,
    ) -> dict[str, Any]:
        """Query all balances using ORM"""
        if timestamp is None:
            timestamp = ts_now()
        
        balances: dict[Location, dict[Asset, Balance]] = {}
        
        # Query exchange balances
        for exchange in self.exchange_manager.iterate_exchanges():
            try:
                exchange_balances = exchange.query_balances()
                location = exchange.location
                if location not in balances:
                    balances[location] = {}
                balances[location].update(exchange_balances)
            except Exception as e:
                log.error(f'Failed to query {exchange.name} balances: {e}')
                self.msg_aggregator.add_error(
                    f'Failed to query {exchange.name} balances: {str(e)}'
                )
                if not save_despite_errors:
                    continue
        
        # Query blockchain balances
        try:
            blockchain_balances = self.chains_aggregator.query_balances(
                blockchain=None,
                force_token_detection=False,
                ignore_cache=ignore_cache,
            )
            for blockchain, assets in blockchain_balances.items():
                location = Location.from_chain_id(blockchain)
                if location not in balances:
                    balances[location] = {}
                balances[location].update(assets)
        except Exception as e:
            log.error(f'Failed to query blockchain balances: {e}')
            self.msg_aggregator.add_error(
                f'Failed to query blockchain balances: {str(e)}'
            )
        
        # Add manual balances
        manual_balances = self.db.repos.manual_balances.get_all_balances()
        for manual_balance in manual_balances:
            location = Location.deserialize_from_db(manual_balance.location)
            asset = Asset(manual_balance.asset)
            balance = Balance(amount=manual_balance.amount)
            
            if location not in balances:
                balances[location] = {}
            if asset in balances[location]:
                balances[location][asset] += balance
            else:
                balances[location][asset] = balance
        
        # Save to database if requested
        if requested_save_data:
            self._save_balances_to_database(timestamp, balances)
        
        return {
            'timestamp': timestamp,
            'balances': balances,
        }

    def _save_balances_to_database(
            self,
            timestamp: Timestamp,
            balances: dict[Location, dict[Asset, Balance]],
    ) -> None:
        """Save balance snapshot to database using ORM"""
        with self.db.repos.unit_of_work():
            # Create balance snapshot
            snapshot_id = self.db.repos.balance_snapshots.create_snapshot(timestamp)
            
            # Save individual balances
            for location, location_balances in balances.items():
                for asset, balance in location_balances.items():
                    self.db.repos.balance_snapshots.add_balance_to_snapshot(
                        snapshot_id=snapshot_id,
                        location=location.serialize_for_db(),
                        asset=asset.identifier,
                        amount=str(balance.amount),
                        usd_value=str(balance.usd_value) if balance.usd_value else None,
                    )

    def get_latest_balance_snapshot(self) -> dict[str, Any] | None:
        """Get the latest balance snapshot using ORM"""
        snapshot = self.db.repos.balance_snapshots.get_latest_snapshot()
        
        if not snapshot:
            return None
        
        # Get balances for this snapshot
        balances = self.db.repos.balance_snapshots.get_snapshot_balances(snapshot.identifier)
        
        # Convert to expected format
        result_balances: dict[Location, dict[Asset, Balance]] = {}
        
        for balance_entry in balances:
            location = Location.deserialize_from_db(balance_entry.location)
            asset = Asset(balance_entry.asset)
            balance = Balance(
                amount=balance_entry.amount,
                usd_value=balance_entry.usd_value,
            )
            
            if location not in result_balances:
                result_balances[location] = {}
            result_balances[location][asset] = balance
        
        return {
            'timestamp': snapshot.timestamp,
            'balances': result_balances,
        }

    def get_balance_history(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            location: Location | None = None,
            asset: Asset | None = None,
    ) -> list[dict[str, Any]]:
        """Get balance history between timestamps using ORM"""
        snapshots = self.db.repos.balance_snapshots.get_snapshots_in_range(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        
        history = []
        for snapshot in snapshots:
            balances = self.db.repos.balance_snapshots.get_snapshot_balances(
                snapshot_id=snapshot.identifier,
                location=location.serialize_for_db() if location else None,
                asset=asset.identifier if asset else None,
            )
            
            # Convert to expected format
            snapshot_data = {
                'timestamp': snapshot.timestamp,
                'balances': defaultdict(dict),
            }
            
            for balance_entry in balances:
                loc = Location.deserialize_from_db(balance_entry.location)
                ast = Asset(balance_entry.asset)
                bal = Balance(
                    amount=balance_entry.amount,
                    usd_value=balance_entry.usd_value,
                )
                snapshot_data['balances'][loc][ast] = bal
            
            history.append(snapshot_data)
        
        return history

    def query_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query history events from external sources and save to database"""
        # Query exchange history
        for exchange in self.exchange_manager.iterate_exchanges():
            try:
                log.info(f'Querying {exchange.name} history events')
                # TODO: Each exchange would need to implement query_history_events
                # TODO: that returns HistoryEvent objects
                # events = exchange.query_history_events(from_timestamp, to_timestamp)
                # self.add_history_events(events)
            except Exception as e:
                log.error(f'Failed to query {exchange.name} history: {e}')
                self.msg_aggregator.add_error(
                    f'Failed to query {exchange.name} history: {str(e)}'
                )
        
        # Query blockchain history
        try:
            log.info('Querying blockchain history events')
            # TODO: Chains aggregator would need to implement query_history_events
            # events = self.chains_aggregator.query_history_events(from_timestamp, to_timestamp)
            # self.add_history_events(events)
        except Exception as e:
            log.error(f'Failed to query blockchain history: {e}')
            self.msg_aggregator.add_error(
                f'Failed to query blockchain history: {str(e)}'
            )