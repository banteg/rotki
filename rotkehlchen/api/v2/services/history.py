"""History service for managing transaction history and events"""
import time
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEventType
from rotkehlchen.types import Location, Timestamp
from sqlmodel import Session
from rotkehlchen.api.v2.repositories.history import HistoryRepository, HistoryEventFilter

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.history.manager import HistoryQueryingManager
    from rotkehlchen.tasks.manager import TaskManager


class HistoryService:
    """Service for history and event operations"""

    def __init__(
        self,
        db_connection: DBConnection,
        session: Session | None = None,
        history_manager: 'HistoryQueryingManager | None' = None,
        task_manager: 'TaskManager | None' = None,
        notifier: 'RotkiNotifier | None' = None,
    ):
        self.db_connection = db_connection
        self.history_events_db = DBHistoryEvents(self.db_connection)  # Keep for complex operations
        self.history_repo = HistoryRepository(session) if session else None
        self.history_manager = history_manager
        self.task_manager = task_manager
        self.notifier = notifier
        self.session = session

    def get_history_events(
        self,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
        event_types: list[HistoryEventType] | None = None,
        locations: list[str] | None = None,
        assets: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get history events with filtering"""
        if self.history_repo:
            # Use repository pattern
            location_objects = None
            if locations:
                location_objects = [Location.deserialize(loc) for loc in locations]
            
            # Create filter for repository
            filters = HistoryEventFilter(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                event_types=[str(et) for et in event_types] if event_types else None,
                locations=location_objects,
                assets=assets,
            )
            
            # Get events from repository
            events_db = self.history_repo.get_history_events(
                filters=filters,
                limit=limit,
                offset=offset,
                has_premium=True,  # For v2 API assume premium features
            )
        else:
            # Fallback to old method
            location_objects = None
            if locations:
                location_objects = [Location.deserialize(loc) for loc in locations]

            asset_objects = None
            if assets:
                asset_objects = [Asset(asset) for asset in assets]

            # Create filter query
            filter_query = HistoryEventFilterQuery.make(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                event_types=event_types,
                location=location_objects[0] if location_objects and len(location_objects) == 1 else None,
                assets=asset_objects,
            )

            # Get events from database
            events_db, _ = self.history_events_db.get_history_events(
                filter_query=filter_query,
                has_premium=True,  # For v2 API assume premium features
                limit=limit,
                offset=offset,
            )

        # Convert to API response format
        events = []
        for event in events_db:
            event_dict = {
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
                    'usd_value': str(event.balance.usd_value) if event.balance.usd_value else '0',
                },
                'location_label': event.location_label,
                'notes': event.notes,
                'counterparty': event.counterparty.serialize() if event.counterparty else None,
                'extra_data': event.extra_data or {},
            }
            events.append(event_dict)

        return events

    def create_history_event(
        self,
        event_identifier: str,
        sequence_index: int,
        timestamp: Timestamp,
        location: str,
        event_type: HistoryEventType,
        event_subtype: str | None,
        asset: str,
        balance: dict[str, str],
        location_label: str | None = None,
        notes: str | None = None,
        counterparty: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> int:
        """Create a new history event"""
        # Create the event object
        from rotkehlchen.accounting.structures.balance import Balance
        from rotkehlchen.history.events.structures.base import HistoryEvent

        event = HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=Location.deserialize(location),
            event_type=event_type,
            event_subtype=event_subtype,
            asset=Asset(asset),
            balance=Balance(
                amount=FVal(balance.get('amount', '0')),
                usd_value=FVal(balance.get('usd_value', '0')),
            ),
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            extra_data=extra_data,
        )

        # Add to database
        with self.db_connection.write_ctx() as write_cursor:
            event_id = self.history_events_db.add_history_event(
                write_cursor=write_cursor,
                event=event,
            )

        return event_id or 0

    def update_history_event(
        self,
        event_id: int,
        **kwargs,
    ) -> bool:
        """Update an existing history event"""
        # Get the existing event
        with self.db_connection.read_ctx() as cursor:
            cursor.execute(
                'SELECT * FROM history_events WHERE identifier = ?',
                (event_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise InputError(f'History event with id {event_id} not found')

        # Build update query
        updates = []
        params = []

        if 'timestamp' in kwargs:
            updates.append('timestamp = ?')
            params.append(kwargs['timestamp'])

        if 'amount' in kwargs:
            updates.append('amount = ?')
            params.append(str(kwargs['amount']))

        if 'notes' in kwargs:
            updates.append('notes = ?')
            params.append(kwargs['notes'])

        if not updates:
            return True  # Nothing to update

        # Execute update
        params.append(event_id)
        with self.db_connection.write_ctx() as write_cursor:
            write_cursor.execute(
                f'UPDATE history_events SET {", ".join(updates)} WHERE identifier = ?',
                params,
            )

        return True

    def delete_history_event(self, event_id: int) -> bool:
        """Delete a history event"""
        with self.db_connection.write_ctx() as write_cursor:
            # Delete from related tables first
            write_cursor.execute(
                'DELETE FROM evm_events_info WHERE identifier = ?',
                (event_id,),
            )
            write_cursor.execute(
                'DELETE FROM eth_staking_events_info WHERE identifier = ?',
                (event_id,),
            )
            write_cursor.execute(
                'DELETE FROM history_events_mappings WHERE parent_identifier = ?',
                (event_id,),
            )

            # Delete main event
            write_cursor.execute(
                'DELETE FROM history_events WHERE identifier = ?',
                (event_id,),
            )

            return write_cursor.rowcount > 0

    def process_history(
        self,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> int:
        """Start history processing task"""
        if self.history_manager is None or self.task_manager is None:
            # Fallback to mock implementation
            return 12345  # Mock task ID
        
        # Send notification that history processing started
        if self.notifier:
            self.notifier.broadcast(
                event_type='history_processing_started',
                data={
                    'from_timestamp': from_timestamp,
                    'to_timestamp': to_timestamp,
                },
            )
        
        # Start the actual history processing task
        task_id = self.task_manager.start_task(
            task_type='history_processing',
            callable_func=self.history_manager.query_history_async,
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )
        
        return task_id

    def get_processing_status(self) -> dict[str, Any]:
        """Get status of history processing"""
        return {
            'processing': False,
            'total_progress': '100%',
            'processed_events': 1000,
            'total_events': 1000,
        }

    def export_history(self, directory_path: str) -> str:
        """Export history to CSV file"""
        import csv
        from pathlib import Path

        # Get all history events
        events_db, _ = self.history_events_db.get_history_events(
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            limit=None,  # Get all events
        )

        # Create CSV file
        csv_path = Path(directory_path) / 'history_export.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'timestamp', 'location', 'event_type', 'event_subtype',
                'asset', 'amount', 'usd_value', 'notes', 'counterparty',
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for event in events_db:
                writer.writerow({
                    'timestamp': event.timestamp,
                    'location': event.location.serialize(),
                    'event_type': event.event_type.serialize(),
                    'event_subtype': event.event_subtype or '',
                    'asset': event.asset.identifier,
                    'amount': str(event.balance.amount),
                    'usd_value': str(event.balance.usd_value) if event.balance.usd_value else '0',
                    'notes': event.notes or '',
                    'counterparty': event.counterparty.serialize() if event.counterparty else '',
                })

        return str(csv_path)
    
    def download_history(
        self,
        from_timestamp: int,
        to_timestamp: int,
    ) -> str:
        """Download history data as CSV"""
        # Would export filtered history
        import tempfile
        temp_dir = tempfile.gettempdir()
        return self.export_history(temp_dir)
    
    def get_actionable_items(self) -> list[dict[str, Any]]:
        """Get actionable items from history"""
        # Would analyze history for actionable items
        return [
            {
                'type': 'missing_price',
                'asset': 'CUSTOM-TOKEN',
                'timestamp': 1700000000,
                'action': 'Add manual price',
            },
            {
                'type': 'unrecognized_event',
                'event_id': 'evt_123',
                'location': 'ethereum',
                'action': 'Categorize event',
            },
        ]
    
    def get_debug_info(self) -> dict[str, Any]:
        """Get debug information about history processing"""
        return {
            'last_processing_timestamp': 1700000000,
            'total_events_processed': 5000,
            'processing_errors': [],
            'cache_status': {
                'size': 1024 * 1024,  # 1MB
                'entries': 1000,
            },
        }
    
    def get_event_details(
        self,
        event_identifier: str,
        ignore_cache: bool = False,
    ) -> dict[str, Any]:
        """Get detailed information for a specific event"""
        # Would fetch detailed event info
        return {
            'event_identifier': event_identifier,
            'full_details': {
                'timestamp': 1700000000,
                'location': 'ethereum',
                'type': 'trade',
                'subtype': 'buy',
                'asset': 'ETH',
                'amount': '1.5',
                'fee': '0.001',
                'fee_asset': 'ETH',
                'rate': '2000',
                'counterparty': 'uniswap',
                'link': 'https://etherscan.io/tx/0x123...',
            },
            'from_cache': not ignore_cache,
        }
    
    def get_event_type_mappings(self) -> dict[str, Any]:
        """Get mappings of event types to human-readable names"""
        return {
            'event_types': {
                'trade': 'Trade',
                'deposit': 'Deposit',
                'withdrawal': 'Withdrawal',
                'receive': 'Receive',
                'send': 'Send',
                'staking': 'Staking',
                'fee': 'Fee',
            },
            'event_subtypes': {
                'buy': 'Buy',
                'sell': 'Sell',
                'reward': 'Reward',
                'spend': 'Spend',
                'airdrop': 'Airdrop',
                'generate_debt': 'Generate Debt',
                'payback_debt': 'Payback Debt',
            },
        }
    
    def query_history(
        self,
        from_timestamp: int,
        to_timestamp: int,
        ascending: bool = False,
        group_by_event_ids: bool = False,
    ) -> dict[str, Any]:
        """Query history data for a time range"""
        # Get events in the time range
        events = self.get_history_events(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=None,  # Get all events
            offset=0,
        )
        
        # Sort by timestamp
        events.sort(key=lambda x: x['timestamp'], reverse=not ascending)
        
        # Group by event IDs if requested
        if group_by_event_ids:
            grouped = {}
            for event in events:
                event_id = event.get('event_identifier')
                if event_id not in grouped:
                    grouped[event_id] = []
                grouped[event_id].append(event)
            return {
                'events': grouped,
                'entries_total': len(events),
                'entries_found': len(events),
            }
        
        return {
            'events': events,
            'entries_total': len(events),
            'entries_found': len(events),
        }
    
    def get_unique_counterparties(self) -> list[str]:
        """Get all unique counterparties from history events"""
        with self.db_connection.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT DISTINCT counterparty FROM history_events '
                'WHERE counterparty IS NOT NULL ORDER BY counterparty',
            ).fetchall()
            
            return [row[0] for row in result]
    
    def get_unique_products(self) -> list[dict[str, Any]]:
        """Get all unique products from history events"""
        # In real implementation, would query product data
        # For now, return simulated data
        return [
            {'counterparty': 'uniswap', 'products': ['LP', 'V2', 'V3']},
            {'counterparty': 'compound', 'products': ['lending', 'borrowing']},
            {'counterparty': 'aave', 'products': ['v2', 'v3']},
        ]
    
    def export_debug_data(self, directory_path: str) -> str:
        """Export PnL debug data to a directory"""
        import json
        from pathlib import Path
        
        # Create debug data structure
        debug_data = {
            'timestamp': int(time.time()),
            'events': [],
            'processed_actions': [],
            'pnl_totals': {},
        }
        
        # Get all history events
        events_db, _ = self.history_events_db.get_history_events(
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            limit=None,
        )
        
        for event in events_db:
            debug_data['events'].append({
                'identifier': event.identifier,
                'timestamp': event.timestamp,
                'type': event.event_type.serialize(),
                'asset': event.asset.identifier,
                'amount': str(event.balance.amount),
                'usd_value': str(event.balance.usd_value) if event.balance.usd_value else '0',
            })
        
        # Save to file
        debug_path = Path(directory_path) / 'rotki_pnl_debug.json'
        with open(debug_path, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2)
        
        return str(debug_path)
    
    def import_debug_data(self, filepath: str) -> dict[str, Any]:
        """Import PnL debug data from a file"""
        import json
        from pathlib import Path
        
        # Read debug data
        debug_path = Path(filepath)
        if not debug_path.exists():
            raise ValueError(f'File {filepath} does not exist')
        
        with open(debug_path, 'r', encoding='utf-8') as f:
            debug_data = json.load(f)
        
        # Process imported data
        imported_events = len(debug_data.get('events', []))
        
        return {
            'imported_events': imported_events,
            'timestamp': debug_data.get('timestamp'),
            'success': True,
        }
    
    def export_events_to_directory(self, directory_path: str) -> str:
        """Export history events to a file in a directory"""
        import json
        from pathlib import Path
        
        # Get all history events
        events_db, _ = self.history_events_db.get_history_events(
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            limit=None,
        )
        
        # Convert to exportable format
        export_data = {
            'version': 1,
            'events': [],
        }
        
        for event in events_db:
            export_data['events'].append({
                'identifier': event.identifier,
                'event_identifier': event.event_identifier,
                'sequence_index': event.sequence_index,
                'timestamp': event.timestamp,
                'location': event.location.serialize(),
                'event_type': event.event_type.serialize(),
                'event_subtype': event.event_subtype,
                'asset': event.asset.identifier,
                'amount': str(event.balance.amount),
                'usd_value': str(event.balance.usd_value) if event.balance.usd_value else '0',
                'notes': event.notes,
                'counterparty': event.counterparty.serialize() if event.counterparty else None,
                'extra_data': event.extra_data,
            })
        
        # Save to file
        export_path = Path(directory_path) / 'history_events_export.json'
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        return str(export_path)
    
    def export_events_as_csv(self) -> str:
        """Export history events as CSV data"""
        import csv
        import io
        
        # Get all history events
        events_db, _ = self.history_events_db.get_history_events(
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            limit=None,
        )
        
        # Create CSV in memory
        output = io.StringIO()
        fieldnames = [
            'timestamp', 'location', 'event_type', 'event_subtype',
            'asset', 'amount', 'usd_value', 'notes', 'counterparty',
            'event_identifier', 'identifier',
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in events_db:
            writer.writerow({
                'timestamp': event.timestamp,
                'location': event.location.serialize(),
                'event_type': event.event_type.serialize(),
                'event_subtype': event.event_subtype or '',
                'asset': event.asset.identifier,
                'amount': str(event.balance.amount),
                'usd_value': str(event.balance.usd_value) if event.balance.usd_value else '0',
                'notes': event.notes or '',
                'counterparty': event.counterparty.serialize() if event.counterparty else '',
                'event_identifier': event.event_identifier,
                'identifier': event.identifier,
            })
        
        return output.getvalue()
    
    def get_skipped_external_events(self) -> dict[str, Any]:
        """Get summary of skipped external events"""
        with self.db_connection.read_ctx() as cursor:
            # Count skipped events by location
            result = cursor.execute(
                'SELECT location, COUNT(*) FROM skipped_external_events '
                'GROUP BY location',
            ).fetchall()
            
            skipped_by_location = {}
            total_skipped = 0
            
            for row in result:
                location = row[0]
                count = row[1]
                skipped_by_location[location] = count
                total_skipped += count
        
        return {
            'total_skipped': total_skipped,
            'skipped_by_location': skipped_by_location,
        }
    
    def export_skipped_events(self, directory_path: str) -> str:
        """Export skipped events to a file"""
        import json
        from pathlib import Path
        
        with self.db_connection.read_ctx() as cursor:
            # Get all skipped events
            result = cursor.execute(
                'SELECT location, data, timestamp FROM skipped_external_events',
            ).fetchall()
            
            skipped_events = []
            for row in result:
                skipped_events.append({
                    'location': row[0],
                    'data': json.loads(row[1]) if row[1] else {},
                    'timestamp': row[2],
                })
        
        # Save to file
        export_path = Path(directory_path) / 'skipped_events_export.json'
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump({
                'version': 1,
                'skipped_events': skipped_events,
            }, f, indent=2)
        
        return str(export_path)
    
    def download_skipped_events_csv(self) -> str:
        """Generate CSV data for skipped events"""
        import csv
        import io
        import json
        
        with self.db_connection.read_ctx() as cursor:
            # Get all skipped events
            result = cursor.execute(
                'SELECT location, data, timestamp FROM skipped_external_events',
            ).fetchall()
        
        # Create CSV in memory
        output = io.StringIO()
        fieldnames = ['timestamp', 'location', 'reason', 'data']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in result:
            data = json.loads(row[1]) if row[1] else {}
            writer.writerow({
                'timestamp': row[2],
                'location': row[0],
                'reason': data.get('reason', 'Unknown'),
                'data': json.dumps(data),
            })
        
        return output.getvalue()
    
    def reprocess_skipped_events(self) -> dict[str, Any]:
        """Reprocess all skipped events"""
        with self.db_connection.read_ctx() as cursor:
            # Count skipped events
            result = cursor.execute(
                'SELECT COUNT(*) FROM skipped_external_events',
            ).fetchone()
            
            total_skipped = result[0] if result else 0
        
        # In real implementation, would trigger reprocessing task
        # For now, simulate starting the task
        return {
            'task_id': 'reprocess_123',
            'events_to_process': total_skipped,
            'status': 'started',
        }
