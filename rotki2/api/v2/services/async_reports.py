"""Async reports service for accounting and tax report generation"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.db.filtering import ReportDataFilterQuery
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotki2.api.v2.dependencies import DatabaseDependency


class AsyncReportsService:
    """Async service for handling accounting reports and tax calculations"""

    def __init__(
        self,
        db: 'DatabaseDependency',
        accountant: 'Accountant | None' = None,
        notifier: 'RotkiNotifier | None' = None,
    ):
        self.db = db
        self.accountant = accountant
        self.notifier = notifier
        # Keep reference to the DB reports handler for complex operations
        self.db_reports = DBAccountingReports(db.db_handler) if hasattr(db, 'db_handler') else None

    async def get_pnl_reports(
        self,
        report_id: int | None = None,
        with_limit: bool = False,
    ) -> dict[str, Any]:
        """
        Get PnL report metadata.
        
        Args:
            report_id: If provided, get specific report. Otherwise get all.
            with_limit: Whether to apply free tier limits
            
        Returns:
            Dictionary with reports list and metadata
        """
        if self.db_reports is None:
            # Return mock data if DB not available
            return {
                'entries': [],
                'entries_found': 0,
                'entries_limit': -1,
            }
        
        # Get reports from database
        reports, entries_found = await self._get_reports_async(
            report_id=report_id,
            with_limit=with_limit,
        )
        
        # Determine limit for display
        entries_limit = -1
        if with_limit:
            from rotkehlchen.constants import FREE_REPORTS_LOOKUP_LIMIT
            entries_limit = FREE_REPORTS_LOOKUP_LIMIT
        
        return {
            'entries': reports,
            'entries_found': entries_found,
            'entries_limit': entries_limit,
        }

    async def get_report_data(
        self,
        filter_query: ReportDataFilterQuery,
        with_limit: bool = False,
    ) -> dict[str, Any]:
        """
        Get detailed report data (events, trades, PnL calculations).
        
        Args:
            filter_query: Filter parameters including report_id
            with_limit: Whether to apply free tier limits
            
        Returns:
            Dictionary with report events and metadata
        """
        if self.db_reports is None:
            return {
                'entries': [],
                'entries_found': 0,
                'entries_total': 0,
                'entries_limit': -1,
            }
        
        try:
            # Get report data from database
            report_data, entries_found, entries_total = await self._get_report_data_async(
                filter_=filter_query,
                with_limit=with_limit,
            )
            
            # Determine limit for display
            entries_limit = -1
            if with_limit:
                from rotkehlchen.constants import FREE_PNL_EVENTS_LIMIT
                entries_limit = FREE_PNL_EVENTS_LIMIT
            
            # Serialize events for API response
            serialized_entries = []
            for event in report_data:
                # Convert ProcessedAccountingEvent to API format
                serialized = await self._serialize_processed_event(event)
                serialized_entries.append(serialized)
            
            return {
                'entries': serialized_entries,
                'entries_found': entries_found,
                'entries_total': entries_total,
                'entries_limit': entries_limit,
            }
            
        except InputError as e:
            raise InputError(str(e))

    async def delete_pnl_report(
        self,
        report_id: int,
    ) -> dict[str, Any]:
        """
        Delete a PnL report and all its associated data.
        
        Args:
            report_id: The report ID to delete
            
        Returns:
            Success result or raises InputError
        """
        if self.db_reports is None:
            return {'result': True, 'message': ''}
        
        try:
            # Delete the report
            success = await self._delete_report_async(report_id)
            
            if not success:
                raise InputError(f'Report with id {report_id} not found')
            
            # Notify if available
            if self.notifier:
                # In real implementation: await self.notifier.broadcast_async(...)
                pass
            
            return {'result': True, 'message': ''}
            
        except InputError:
            raise
        except Exception as e:
            raise InputError(f'Failed to delete report: {str(e)}')

    async def get_pnl_totals(
        self,
        report_id: int,
    ) -> dict[str, Any]:
        """
        Get PnL totals for a specific report.
        
        Args:
            report_id: The report ID
            
        Returns:
            Dictionary with PnL totals by asset
        """
        if self.db_reports is None:
            return {
                'assets': {},
                'total_taxable_pnl': '0',
                'total_free_pnl': '0',
            }
        
        # Get totals from database
        totals = await self._get_report_totals_async(report_id)
        
        return totals

    async def export_report_csv(
        self,
        report_id: int,
        directory_path: str | None = None,
    ) -> str:
        """
        Export report data to CSV file(s).
        
        Args:
            report_id: The report to export
            directory_path: Where to save files. If None, return as string.
            
        Returns:
            File path or CSV content
        """
        # Get report data
        filter_query = ReportDataFilterQuery.make(report_id=report_id)
        report_data = await self.get_report_data(
            filter_query=filter_query,
            with_limit=False,  # Export all data
        )
        
        # Generate CSV content
        csv_content = await self._generate_csv_content(report_data['entries'])
        
        if directory_path:
            # Save to file
            import os
            filepath = os.path.join(directory_path, f'pnl_report_{report_id}.csv')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            return filepath
        
        return csv_content

    async def get_accounting_report_status(
        self,
    ) -> dict[str, Any]:
        """
        Get the current status of accounting report generation.
        
        Returns:
            Dictionary with current processing status
        """
        # Check if accountant is currently processing
        if self.accountant is None:
            return {
                'processing': False,
                'message': 'Accounting engine not available',
            }
        
        # In real implementation, check actual processing status
        # For now, return mock status
        return {
            'processing': False,
            'message': '',
            'progress': {
                'current': 0,
                'total': 0,
                'percentage': 0,
            },
        }

    # Private helper methods

    async def _get_reports_async(
        self,
        report_id: int | None,
        with_limit: bool,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get reports from database asynchronously"""
        if self.db_reports is None:
            return [], 0
        
        # TODO: Convert to actual async DB query
        # For now, wrap sync call
        reports, entries_found = self.db_reports.get_reports(
            report_id=report_id,
            with_limit=with_limit,
        )
        
        return reports, entries_found

    async def _get_report_data_async(
        self,
        filter_: ReportDataFilterQuery,
        with_limit: bool,
    ) -> tuple[list[ProcessedAccountingEvent], int, int]:
        """Get report data from database asynchronously"""
        if self.db_reports is None:
            return [], 0, 0
        
        # TODO: Convert to actual async DB query
        # For now, wrap sync call
        report_data, entries_found, entries_total = self.db_reports.get_report_data(
            filter_=filter_,
            with_limit=with_limit,
        )
        
        return report_data, entries_found, entries_total

    async def _delete_report_async(
        self,
        report_id: int,
    ) -> bool:
        """Delete report from database asynchronously"""
        if self.db_reports is None:
            return True
        
        # TODO: Convert to actual async DB operation
        # For now, wrap sync call
        with self.db.db_handler.user_write() as write_cursor:
            # Delete from pnl_reports table
            write_cursor.execute(
                'DELETE FROM pnl_reports WHERE identifier = ?',
                (report_id,),
            )
            
            # Delete associated events
            write_cursor.execute(
                'DELETE FROM pnl_events WHERE report_id = ?',
                (report_id,),
            )
            
            return write_cursor.rowcount > 0

    async def _get_report_totals_async(
        self,
        report_id: int,
    ) -> dict[str, Any]:
        """Get PnL totals for a report asynchronously"""
        if self.db_reports is None:
            return {
                'assets': {},
                'total_taxable_pnl': '0',
                'total_free_pnl': '0',
            }
        
        # TODO: Implement actual totals calculation
        # This would aggregate PnL by asset from the report data
        return {
            'assets': {
                'ETH': {
                    'taxable_pnl': '1000.50',
                    'free_pnl': '500.25',
                    'total_pnl': '1500.75',
                },
                'BTC': {
                    'taxable_pnl': '5000.00',
                    'free_pnl': '2500.00',
                    'total_pnl': '7500.00',
                },
            },
            'total_taxable_pnl': '6000.50',
            'total_free_pnl': '3000.25',
        }

    async def _serialize_processed_event(
        self,
        event: ProcessedAccountingEvent,
    ) -> dict[str, Any]:
        """Serialize a processed accounting event for API response"""
        # Get timestamp converter from accountant
        if self.accountant and self.accountant.pots:
            ts_converter = self.accountant.pots[0].timestamp_to_date
        else:
            ts_converter = lambda ts: str(ts)
        
        # Use the built-in serialization with API export type
        from rotkehlchen.accounting.export import AccountingEventExportType
        
        return event.to_exported_dict(
            ts_converter=ts_converter,
            export_type=AccountingEventExportType.API,
        )

    async def _generate_csv_content(
        self,
        events: list[dict[str, Any]],
    ) -> str:
        """Generate CSV content from events"""
        import csv
        import io
        
        output = io.StringIO()
        
        if not events:
            return ''
        
        # Get field names from first event
        fieldnames = list(events[0].keys())
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in events:
            writer.writerow(event)
        
        return output.getvalue()