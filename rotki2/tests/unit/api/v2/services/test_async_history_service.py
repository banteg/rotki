"""Tests for AsyncHistoryService"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent, HistoryEventType
from rotkehlchen.types import Location, Timestamp

from rotki2.api.v2.repositories.history_events import HistoryEventsRepository
from rotki2.api.v2.repositories.history import HistoryEventFilter
from rotki2.api.v2.services.async_history import AsyncHistoryService


@pytest.fixture
def mock_db():
    """Mock database dependency"""
    db = MagicMock()
    db.async_db_session = MagicMock()
    return db


@pytest.fixture
def mock_history_repo():
    """Mock history repository"""
    return AsyncMock(spec=HistoryEventsRepository)


@pytest.fixture
def async_history_service(mock_db, mock_history_repo):
    """Create AsyncHistoryService instance with mocks"""
    return AsyncHistoryService(
        db=mock_db,
        history_repo=mock_history_repo,
    )


class TestAsyncHistoryService:
    """Test AsyncHistoryService methods"""

    @pytest.mark.asyncio
    async def test_process_history_without_manager(self, async_history_service):
        """Test process_history returns mock data when no history manager"""
        report_id, error = await async_history_service.process_history(
            from_timestamp=Timestamp(1609459200),  # 2021-01-01
            to_timestamp=Timestamp(1640995200),    # 2022-01-01
        )
        
        assert report_id == 12345
        assert error == ''

    @pytest.mark.asyncio
    async def test_get_history_debug_returns_data(self, async_history_service, mock_history_repo):
        """Test get_history_debug returns debug information"""
        # Mock the repository to return some events
        mock_events = [
            HistoryEvent(
                event_identifier='evt_1',
                sequence_index=0,
                timestamp=Timestamp(1609459200),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype='buy',
                asset=Asset('ETH'),
                balance=Balance(amount=FVal('1.5'), usd_value=FVal('3000')),
                notes='Test trade',
            )
        ]
        mock_history_repo.get_history_events.return_value = (mock_events, 1)
        
        # Mock the internal methods
        async_history_service._get_history_events = AsyncMock(return_value=('', mock_events))
        async_history_service._get_settings_async = AsyncMock(return_value={'test': 'settings'})
        async_history_service._get_cache_data_async = AsyncMock(return_value={'cache': 'data'})
        async_history_service._get_ignored_action_ids_async = AsyncMock(return_value=set())
        
        result = await async_history_service.get_history_debug(
            from_timestamp=Timestamp(1609459200),
            to_timestamp=Timestamp(1640995200),
            directory_path=None,
        )
        
        assert result['result'] is not None
        assert result['message'] == ''
        assert 'events' in result['result']
        assert 'settings' in result['result']
        assert 'pnl_settings' in result['result']

    @pytest.mark.asyncio
    async def test_get_history_debug_exports_to_file(self, async_history_service, tmp_path):
        """Test get_history_debug exports to file when directory provided"""
        # Mock empty events
        async_history_service._get_history_events = AsyncMock(return_value=('', []))
        async_history_service._get_settings_async = AsyncMock(return_value={})
        async_history_service._get_cache_data_async = AsyncMock(return_value={})
        async_history_service._get_ignored_action_ids_async = AsyncMock(return_value=set())
        
        result = await async_history_service.get_history_debug(
            from_timestamp=Timestamp(1609459200),
            to_timestamp=Timestamp(1640995200),
            directory_path=tmp_path,
        )
        
        assert result['result'] is True
        assert result['message'] == ''
        
        # Check file was created
        debug_file = tmp_path / 'pnl_debug.json'
        assert debug_file.exists()
        
        # Verify file content
        with open(debug_file) as f:
            data = json.load(f)
            assert 'events' in data
            assert 'settings' in data
            assert 'pnl_settings' in data

    @pytest.mark.asyncio
    async def test_get_history_events(self, async_history_service, mock_history_repo):
        """Test get_history_events delegates to repository"""
        filter_query = HistoryEventFilter(
            from_ts=Timestamp(1609459200),
            to_ts=Timestamp(1640995200),
        )
        
        mock_events = []
        mock_history_repo.get_history_events.return_value = (mock_events, 0)
        
        events, count = await async_history_service.get_history_events(
            filter_query=filter_query,
            has_premium=True,
        )
        
        assert events == mock_events
        assert count == 0
        mock_history_repo.get_history_events.assert_called_once_with(
            filter_query=filter_query,
            has_premium=True,
        )

    @pytest.mark.asyncio
    async def test_add_history_event(self, async_history_service, mock_history_repo):
        """Test add_history_event delegates to repository"""
        event = HistoryEvent(
            event_identifier='evt_test',
            sequence_index=0,
            timestamp=Timestamp(1609459200),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype='buy',
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('1'), usd_value=FVal('2000')),
        )
        
        mock_history_repo.add_history_event.return_value = 123
        
        event_id = await async_history_service.add_history_event(event)
        
        assert event_id == 123
        mock_history_repo.add_history_event.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_edit_history_event_success(self, async_history_service, mock_history_repo):
        """Test successful edit_history_event"""
        event = MagicMock()
        mock_history_repo.edit_history_event.return_value = True
        
        success, error = await async_history_service.edit_history_event(event)
        
        assert success is True
        assert error == ''

    @pytest.mark.asyncio
    async def test_delete_history_events(self, async_history_service, mock_history_repo):
        """Test delete_history_events deletes multiple events"""
        identifiers = [1, 2, 3]
        
        success, error = await async_history_service.delete_history_events(identifiers)
        
        assert success is True
        assert error == ''
        assert mock_history_repo.delete_history_event.call_count == 3

    @pytest.mark.asyncio
    async def test_import_history_debug_invalid_file(self, async_history_service, tmp_path):
        """Test import_history_debug with invalid file"""
        # Create invalid JSON file
        invalid_file = tmp_path / 'invalid.json'
        invalid_file.write_text('{"invalid": "data"}')
        
        result = await async_history_service.import_history_debug(invalid_file)
        
        assert result['result'] is None
        assert 'Invalid debug file format' in result['message']
        assert result['status_code'] == 409

    def test_serialize_event_for_debug(self, async_history_service):
        """Test _serialize_event_for_debug creates proper format"""
        event = HistoryEvent(
            identifier=123,
            event_identifier='evt_test',
            sequence_index=1,
            timestamp=Timestamp(1609459200),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype='buy',
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('1.5'), usd_value=FVal('3000')),
            location_label='My Wallet',
            notes='Test trade',
            counterparty='uniswap',
            extra_data={'tx_hash': '0x123'},
        )
        
        serialized = async_history_service._serialize_event_for_debug(event)
        
        assert serialized['identifier'] == 123
        assert serialized['event_identifier'] == 'evt_test'
        assert serialized['sequence_index'] == 1
        assert serialized['timestamp'] == 1609459200
        assert serialized['location'] == 'ethereum'
        assert serialized['event_type'] == 'trade'
        assert serialized['event_subtype'] == 'buy'
        assert serialized['asset'] == 'ETH'
        assert serialized['balance']['amount'] == '1.5'
        assert serialized['balance']['usd_value'] == '3000'
        assert serialized['location_label'] == 'My Wallet'
        assert serialized['notes'] == 'Test trade'
        assert serialized['counterparty'] == 'uniswap'
        assert serialized['extra_data'] == {'tx_hash': '0x123'}