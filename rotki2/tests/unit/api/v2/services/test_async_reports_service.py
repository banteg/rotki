"""Tests for AsyncReportsService"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.db.filtering import ReportDataFilterQuery
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.errors.misc import InputError

from rotki2.api.v2.services.async_reports import AsyncReportsService


@pytest.fixture
def mock_db():
    """Mock database dependency"""
    db = MagicMock()
    db.db_handler = MagicMock()
    db.db_handler.user_write = MagicMock()
    return db


@pytest.fixture
def mock_db_reports():
    """Mock DBAccountingReports"""
    return MagicMock(spec=DBAccountingReports)


@pytest.fixture
def async_reports_service(mock_db, mock_db_reports):
    """Create AsyncReportsService instance with mocks"""
    service = AsyncReportsService(db=mock_db)
    service.db_reports = mock_db_reports
    return service


class TestAsyncReportsService:
    """Test AsyncReportsService methods"""

    @pytest.mark.asyncio
    async def test_get_pnl_reports_all(self, async_reports_service, mock_db_reports):
        """Test get_pnl_reports returns all reports"""
        mock_reports = [
            {
                'identifier': 1,
                'timestamp': 1609459200,
                'start_ts': 1609459200,
                'end_ts': 1640995200,
                'first_processed_timestamp': 1609459200,
                'last_processed_timestamp': 1640995200,
                'processed_actions': 100,
                'total_actions': 100,
            }
        ]
        mock_db_reports.get_reports.return_value = (mock_reports, 1)
        
        result = await async_reports_service.get_pnl_reports(
            report_id=None,
            with_limit=False,
        )
        
        assert result['entries'] == mock_reports
        assert result['entries_found'] == 1
        assert result['entries_limit'] == -1

    @pytest.mark.asyncio
    async def test_get_pnl_reports_with_limit(self, async_reports_service, mock_db_reports):
        """Test get_pnl_reports with free tier limit"""
        mock_db_reports.get_reports.return_value = ([], 0)
        
        result = await async_reports_service.get_pnl_reports(
            report_id=None,
            with_limit=True,
        )
        
        assert result['entries'] == []
        assert result['entries_found'] == 0
        assert result['entries_limit'] == 20  # FREE_REPORTS_LOOKUP_LIMIT

    @pytest.mark.asyncio
    async def test_get_pnl_reports_specific(self, async_reports_service, mock_db_reports):
        """Test get_pnl_reports for specific report"""
        mock_report = {
            'identifier': 42,
            'timestamp': 1609459200,
        }
        mock_db_reports.get_reports.return_value = ([mock_report], 1)
        
        result = await async_reports_service.get_pnl_reports(
            report_id=42,
            with_limit=False,
        )
        
        assert len(result['entries']) == 1
        assert result['entries'][0]['identifier'] == 42

    @pytest.mark.asyncio
    async def test_get_report_data_success(self, async_reports_service, mock_db_reports):
        """Test get_report_data returns processed events"""
        # Mock processed event
        mock_event = MagicMock(spec=ProcessedAccountingEvent)
        mock_event.to_exported_dict.return_value = {
            'timestamp': '2021-01-01',
            'event_type': 'trade',
            'asset': 'ETH',
            'amount': '1.5',
            'pnl': '100.50',
        }
        
        mock_db_reports.get_report_data.return_value = ([mock_event], 1, 1)
        
        filter_query = ReportDataFilterQuery.make(report_id=1)
        result = await async_reports_service.get_report_data(
            filter_query=filter_query,
            with_limit=False,
        )
        
        assert len(result['entries']) == 1
        assert result['entries'][0]['asset'] == 'ETH'
        assert result['entries_found'] == 1
        assert result['entries_total'] == 1
        assert result['entries_limit'] == -1

    @pytest.mark.asyncio
    async def test_get_report_data_with_input_error(self, async_reports_service, mock_db_reports):
        """Test get_report_data handles InputError"""
        mock_db_reports.get_report_data.side_effect = InputError('Invalid report ID')
        
        filter_query = ReportDataFilterQuery.make(report_id=999)
        
        with pytest.raises(InputError, match='Invalid report ID'):
            await async_reports_service.get_report_data(
                filter_query=filter_query,
                with_limit=False,
            )

    @pytest.mark.asyncio
    async def test_delete_pnl_report_success(self, async_reports_service):
        """Test successful report deletion"""
        # Mock the delete operation
        async_reports_service._delete_report_async = AsyncMock(return_value=True)
        
        result = await async_reports_service.delete_pnl_report(report_id=1)
        
        assert result['result'] is True
        assert result['message'] == ''

    @pytest.mark.asyncio
    async def test_delete_pnl_report_not_found(self, async_reports_service):
        """Test deletion of non-existent report"""
        # Mock the delete operation to return False
        async_reports_service._delete_report_async = AsyncMock(return_value=False)
        
        with pytest.raises(InputError, match='Report with id 999 not found'):
            await async_reports_service.delete_pnl_report(report_id=999)

    @pytest.mark.asyncio
    async def test_get_pnl_totals(self, async_reports_service):
        """Test get_pnl_totals returns totals by asset"""
        # Mock the totals retrieval
        async_reports_service._get_report_totals_async = AsyncMock(
            return_value={
                'assets': {
                    'ETH': {
                        'taxable_pnl': '1000.50',
                        'free_pnl': '500.25',
                        'total_pnl': '1500.75',
                    }
                },
                'total_taxable_pnl': '1000.50',
                'total_free_pnl': '500.25',
            }
        )
        
        result = await async_reports_service.get_pnl_totals(report_id=1)
        
        assert 'ETH' in result['assets']
        assert result['assets']['ETH']['total_pnl'] == '1500.75'
        assert result['total_taxable_pnl'] == '1000.50'

    @pytest.mark.asyncio
    async def test_export_report_csv_to_string(self, async_reports_service):
        """Test export_report_csv returns CSV content as string"""
        # Mock report data
        async_reports_service.get_report_data = AsyncMock(
            return_value={
                'entries': [
                    {
                        'timestamp': '2021-01-01',
                        'event_type': 'trade',
                        'asset': 'ETH',
                        'amount': '1.5',
                    }
                ]
            }
        )
        
        csv_content = await async_reports_service.export_report_csv(
            report_id=1,
            directory_path=None,
        )
        
        assert 'timestamp,event_type,asset,amount' in csv_content
        assert '2021-01-01,trade,ETH,1.5' in csv_content

    @pytest.mark.asyncio
    async def test_export_report_csv_to_file(self, async_reports_service, tmp_path):
        """Test export_report_csv saves to file"""
        # Mock report data
        async_reports_service.get_report_data = AsyncMock(
            return_value={
                'entries': [
                    {
                        'timestamp': '2021-01-01',
                        'event_type': 'trade',
                        'asset': 'ETH',
                        'amount': '1.5',
                    }
                ]
            }
        )
        
        filepath = await async_reports_service.export_report_csv(
            report_id=1,
            directory_path=str(tmp_path),
        )
        
        assert filepath == str(tmp_path / 'pnl_report_1.csv')
        assert (tmp_path / 'pnl_report_1.csv').exists()

    @pytest.mark.asyncio
    async def test_get_accounting_report_status_no_accountant(self, async_reports_service):
        """Test report status when accountant not available"""
        async_reports_service.accountant = None
        
        status = await async_reports_service.get_accounting_report_status()
        
        assert status['processing'] is False
        assert status['message'] == 'Accounting engine not available'

    @pytest.mark.asyncio
    async def test_get_accounting_report_status_with_accountant(self, async_reports_service):
        """Test report status with accountant"""
        async_reports_service.accountant = MagicMock()
        
        status = await async_reports_service.get_accounting_report_status()
        
        assert status['processing'] is False
        assert status['message'] == ''
        assert 'progress' in status

    @pytest.mark.asyncio
    async def test_no_db_reports_fallback(self):
        """Test service works without db_reports"""
        service = AsyncReportsService(db=MagicMock())
        service.db_reports = None
        
        # Test get_pnl_reports
        result = await service.get_pnl_reports()
        assert result['entries'] == []
        
        # Test get_report_data
        filter_query = ReportDataFilterQuery.make(report_id=1)
        result = await service.get_report_data(filter_query)
        assert result['entries'] == []
        
        # Test delete_pnl_report
        result = await service.delete_pnl_report(report_id=1)
        assert result['result'] is True