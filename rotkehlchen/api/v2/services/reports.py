"""Reports service for accounting and tax report generation"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.api.websockets.notifier import RotkiNotifier


class ReportsService:
    """Service for handling accounting reports and tax calculations"""
    
    def __init__(
        self,
        db_service: DatabaseService,
        accountant: 'Accountant | None' = None,
        notifier: 'RotkiNotifier | None' = None,
    ):
        self.db = db_service
        self.accountant = accountant
        self.notifier = notifier
    
    def generate_report(
        self,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
        report_name: str | None = None,
    ) -> int:
        """Generate a new accounting report
        
        Returns:
            The report ID
        """
        if self.accountant is None:
            # Fallback to placeholder if accountant not available
            with self.db.conn.write_ctx() as cursor:
                cursor.execute(
                    '''INSERT INTO reports 
                       (name, start_ts, end_ts, first_processed_timestamp, last_processed_timestamp, 
                        processed_actions, total_actions, identifier)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        report_name or f'Report {from_timestamp}-{to_timestamp}',
                        from_timestamp,
                        to_timestamp,
                        from_timestamp,
                        to_timestamp,
                        0,  # processed_actions
                        0,  # total_actions
                        1,  # identifier (placeholder)
                    ),
                )
                return cursor.lastrowid
        
        # Use the actual accountant to process history
        report_id = self.accountant.process_history(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )
        
        # If we have a notifier, send update
        if self.notifier:
            self.notifier.broadcast(
                event_type='report_started',
                data={'report_id': report_id},
            )
        
        return report_id
    
    def list_reports(self) -> list[dict[str, Any]]:
        """List all available reports"""
        reports = []
        
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                '''SELECT identifier, name, start_ts, end_ts, 
                          first_processed_timestamp, last_processed_timestamp,
                          processed_actions, total_actions
                   FROM reports
                   ORDER BY identifier DESC''',
            )
            
            for row in cursor:
                reports.append({
                    'identifier': row[0],
                    'name': row[1],
                    'start_ts': row[2],
                    'end_ts': row[3],
                    'first_processed_timestamp': row[4],
                    'last_processed_timestamp': row[5],
                    'processed_actions': row[6],
                    'total_actions': row[7],
                    'progress': row[6] / row[7] if row[7] > 0 else 0,
                })
        
        return reports
    
    def get_report(self, report_id: int) -> dict[str, Any] | None:
        """Get report metadata by ID"""
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                '''SELECT identifier, name, start_ts, end_ts,
                          first_processed_timestamp, last_processed_timestamp,
                          processed_actions, total_actions
                   FROM reports
                   WHERE identifier = ?''',
                (report_id,),
            )
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'identifier': row[0],
                'name': row[1],
                'start_ts': row[2],
                'end_ts': row[3],
                'first_processed_timestamp': row[4],
                'last_processed_timestamp': row[5],
                'processed_actions': row[6],
                'total_actions': row[7],
                'progress': row[6] / row[7] if row[7] > 0 else 0,
            }
    
    def get_report_data(
        self,
        report_id: int,
        offset: int = 0,
        limit: int = 500,
    ) -> dict[str, Any] | None:
        """Get report data (events, trades, etc.)"""
        # First check if report exists
        report = self.get_report(report_id)
        if not report:
            return None
        
        # TODO: Implement actual report data retrieval
        # This would query processed events, trades, tax calculations
        # from the report-specific tables
        
        # For now, return placeholder data
        return {
            'report_id': report_id,
            'events': [],
            'trades': [],
            'cost_basis': {},
            'pnl': {
                'taxable': '0',
                'free': '0',
                'total': '0',
            },
            'overview': {
                'total_events': 0,
                'total_trades': 0,
            },
            'offset': offset,
            'limit': limit,
            'total_entries': 0,
        }
    
    def delete_report(self, report_id: int) -> bool:
        """Delete a report and all associated data"""
        with self.db.conn.write_ctx() as cursor:
            # Delete from reports table
            cursor.execute('DELETE FROM reports WHERE identifier = ?', (report_id,))
            
            # TODO: Also delete associated data from:
            # - processed_events
            # - trades
            # - Any other report-specific tables
            
            return cursor.rowcount > 0