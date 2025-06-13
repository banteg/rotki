"""Async history service for managing transaction history and events"""
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotki2.api.v2.repositories.async_history_events import (
    AsyncHistoryEventsRepository,
    HistoryEventFilter,
)
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.misc import AccountingError, InputError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent, HistoryEventType
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.history.manager import HistoryQueryingManager
    from rotki2.api.v2.dependencies import DatabaseDependency


class AsyncHistoryService:
    """Async service for history and event operations"""

    def __init__(
        self,
        db: 'DatabaseDependency',
        history_repo: AsyncHistoryEventsRepository,
        history_manager: 'HistoryQueryingManager | None' = None,
        notifier: 'RotkiNotifier | None' = None,
    ):
        self.db = db
        self.history_repo = history_repo
        self.history_manager = history_manager
        self.notifier = notifier

    async def process_history(
        self,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> tuple[int, str]:
        """
        Process history for the given time range and generate an accounting report.
        
        This method:
        1. Queries history events from various sources
        2. Processes them through the accounting engine
        3. Generates a PnL report
        
        Returns:
            Tuple of (report_id, error_or_empty_string)
        """
        if self.history_manager is None:
            # Return mock data if history manager not available
            return 12345, ''
        
        # Get history events from all sources
        error_or_empty, events = await self._get_history_events(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )
        
        if error_or_empty:
            # If there was an error getting events, still try to process what we have
            # This matches the behavior in rotkehlchen.py
            pass
        
        # Process the events through the accountant
        # Note: In the full async implementation, this would also be async
        # For now, we'll call the sync version as a placeholder
        report_id = await self._process_events_with_accountant(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
            events=events,
        )
        
        return report_id, error_or_empty

    async def get_history_debug(
        self,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
        directory_path: Path | None,
    ) -> dict[str, Any]:
        """
        Export all history events for a timestamp range for PnL debugging.
        Also exports user settings & ignored action identifiers.
        
        Args:
            from_timestamp: Start of the time range
            to_timestamp: End of the time range
            directory_path: If provided, export to file. Otherwise return data.
            
        Returns:
            Dictionary with debug information or success result
        """
        # Get history events
        error_or_empty, events = await self._get_history_events(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )
        
        if error_or_empty:
            return {
                'result': None,
                'message': error_or_empty,
                'status_code': 409,  # Conflict
            }
        
        # Get settings and cache data
        async with self.db.async_db_session() as session:
            settings = await self._get_settings_async(session)
            cache = await self._get_cache_data_async(session)
            ignored_ids = await self._get_ignored_action_ids_async(session)
        
        # Prepare debug info
        debug_info = {
            'events': [self._serialize_event_for_debug(event) for event in events],
            'settings': settings | cache,
            'ignored_events_ids': list(ignored_ids),
            'pnl_settings': {
                'from_timestamp': int(from_timestamp),
                'to_timestamp': int(to_timestamp),
            },
        }
        
        # Export to file if directory provided
        if directory_path is not None:
            filepath = directory_path / 'pnl_debug.json'
            with open(filepath, mode='w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2)
            return {'result': True, 'message': ''}
        
        return {'result': debug_info, 'message': ''}

    async def import_history_debug(self, filepath: Path) -> dict[str, Any]:
        """
        Import PnL debug data for processing and report generation.
        
        This is only available in non-frozen builds (development mode).
        
        Args:
            filepath: Path to the debug JSON file
            
        Returns:
            Success or failure result
        """
        try:
            # Import the debug data
            with open(filepath, encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate the data structure
            if 'events' not in data or 'pnl_settings' not in data:
                return {
                    'result': None,
                    'message': 'Invalid debug file format',
                    'status_code': 409,
                }
            
            # Convert events back to proper objects
            events = []
            for event_data in data['events']:
                # Here we would deserialize the events properly
                # For now, this is a placeholder
                pass
            
            # Process the imported history
            report_id = await self._process_events_with_accountant(
                start_ts=Timestamp(data['pnl_settings']['from_timestamp']),
                end_ts=Timestamp(data['pnl_settings']['to_timestamp']),
                events=events,
            )
            
            return {'result': True, 'message': ''}
            
        except Exception as e:
            return {
                'result': None,
                'message': str(e),
                'status_code': 409,
            }

    async def get_history_events(
        self,
        filter_query: HistoryEventFilter,
        has_premium: bool = True,
    ) -> tuple[list[HistoryEvent], int]:
        """
        Get history events based on filter criteria.
        
        Args:
            filter_query: Filter parameters for querying events
            has_premium: Whether user has premium features
            
        Returns:
            Tuple of (events list, total count)
        """
        return await self.history_repo.get_history_events(
            filter_query=filter_query,
            has_premium=has_premium,
        )

    async def add_history_event(
        self,
        event: HistoryEvent,
    ) -> int:
        """Add a new history event to the database"""
        return await self.history_repo.add_history_event(event)

    async def edit_history_event(
        self,
        event: HistoryEvent,
    ) -> tuple[bool, str]:
        """Edit an existing history event"""
        try:
            success = await self.history_repo.edit_history_event(event)
            return success, ''
        except InputError as e:
            return False, str(e)

    async def delete_history_events(
        self,
        identifiers: list[int],
    ) -> tuple[bool, str]:
        """Delete history events by their identifiers"""
        try:
            for identifier in identifiers:
                await self.history_repo.delete_history_event(identifier)
            return True, ''
        except Exception as e:
            return False, str(e)

    async def get_history_events_count(
        self,
        filter_query: HistoryEventFilter,
    ) -> int:
        """Get count of history events matching the filter"""
        _, count = await self.history_repo.get_history_events(
            filter_query=filter_query,
            has_premium=True,
            limit=0,  # Just get count
        )
        return count

    # Private helper methods
    
    async def _get_history_events(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> tuple[str, list['AccountingEventMixin']]:
        """
        Get all history events in the time range from various sources.
        
        This is a simplified version. The full implementation would:
        1. Query exchanges
        2. Query blockchain transactions
        3. Query external services
        4. Merge and sort all events
        
        Returns:
            Tuple of (error_message, events_list)
        """
        if self.history_manager is None:
            # Return empty events if no history manager
            return '', []
        
        # TODO: Convert history_manager.get_history to async
        # For now, we'll simulate the async behavior
        try:
            # In real implementation, this would be:
            # error_or_empty, events = await self.history_manager.get_history_async(...)
            error_or_empty = ''
            events = []
            
            # Get events from repository
            filter_query = HistoryEventFilter(
                from_ts=start_ts,
                to_ts=end_ts,
            )
            db_events, _ = await self.history_repo.get_history_events(
                filter_query=filter_query,
                has_premium=True,
            )
            events.extend(db_events)
            
            return error_or_empty, events
            
        except Exception as e:
            return str(e), []

    async def _process_events_with_accountant(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        events: list['AccountingEventMixin'],
    ) -> int:
        """
        Process events through the accounting engine to generate PnL report.
        
        TODO: This needs to be converted to async when accountant is converted.
        
        Returns:
            Report ID
        """
        # In the full async implementation, this would call an async accountant
        # For now, return a mock report ID
        mock_report_id = int(time.time())
        
        # Send notification if available
        if self.notifier:
            # In real implementation: await self.notifier.broadcast_async(...)
            pass
        
        return mock_report_id

    async def _get_settings_async(self, session) -> dict[str, Any]:
        """Get user settings asynchronously"""
        # TODO: Implement async settings retrieval
        return {
            'include_crypto_to_crypto': True,
            'include_gas_costs': True,
            'taxable_ledger_actions': [],
        }

    async def _get_cache_data_async(self, session) -> dict[str, Any]:
        """Get cache data asynchronously"""
        # TODO: Implement async cache retrieval
        return {
            'last_data_upload_ts': 0,
            'last_balance_save': 0,
        }

    async def _get_ignored_action_ids_async(self, session) -> set[str]:
        """Get ignored action IDs asynchronously"""
        # TODO: Implement async ignored IDs retrieval
        return set()

    def _serialize_event_for_debug(self, event: 'HistoryEvent') -> dict[str, Any]:
        """Serialize an event for debug export"""
        return {
            'identifier': event.identifier,
            'event_identifier': event.event_identifier,
            'sequence_index': event.sequence_index,
            'timestamp': event.timestamp,
            'location': event.location.serialize(),
            'event_type': event.event_type.serialize(),
            'event_subtype': event.event_subtype,
            'asset': event.asset.identifier,
            'balance': {
                'amount': str(event.balance.amount),
                'usd_value': str(event.balance.usd_value) if event.balance.usd_value else None,
            },
            'location_label': event.location_label,
            'notes': event.notes,
            'counterparty': event.counterparty.serialize() if event.counterparty else None,
            'extra_data': event.extra_data,
        }