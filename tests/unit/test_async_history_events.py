"""Tests for async history events repository and service."""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rotkehlchen.api.v2.repositories.async_history_events import AsyncHistoryEventsRepository
from rotkehlchen.api.v2.services.async_history_events import AsyncHistoryEventsService
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, Timestamp




@pytest.fixture
async def history_events_repository(
    async_session: AsyncSession,
) -> AsyncHistoryEventsRepository:
    """Create an async history events repository instance."""
    return AsyncHistoryEventsRepository(async_session)


@pytest.fixture
async def history_events_service(
    history_events_repository: AsyncHistoryEventsRepository,
) -> AsyncHistoryEventsService:
    """Create an async history events service instance."""
    return AsyncHistoryEventsService(
        history_events_repository=history_events_repository,
        notifier=None,
    )


@pytest.fixture
def sample_history_event() -> HistoryEvent:
    """Create a sample history event for testing."""
    return HistoryEvent(
        event_identifier='test_event_1',
        sequence_index=0,
        timestamp=Timestamp(1640000000),
        location=Location.KRAKEN,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset='ETH',
        balance=FVal('1.5'),
        location_label='My Kraken Account',
        notes='Test trade',
    )


@pytest.mark.asyncio
async def test_add_history_event_raw_sql(async_session: AsyncSession):
    """Test adding a history event using raw SQL."""
    # Insert event
    result = await async_session.execute(text("""
        INSERT INTO history_events (
            event_identifier, sequence_index, timestamp, location, location_label,
            asset, amount, usd_value, notes, type, subtype, entry_type
        ) VALUES (
            :event_id, :seq, :ts, :loc, :label,
            :asset, :amount, :usd, :notes, :type, :subtype, :entry_type
        ) RETURNING identifier
    """), {
        'event_id': 'test_event_1',
        'seq': 0,
        'ts': 1640000000,
        'loc': 'kraken',
        'label': 'My Account',
        'asset': 'ETH',
        'amount': '1.5',
        'usd': '4500.0',
        'notes': 'Test event',
        'type': 'trade',
        'subtype': 'spend',
        'entry_type': 1,
    })
    
    identifier = result.scalar()
    assert identifier > 0
    
    # Verify event was created
    result = await async_session.execute(
        text("SELECT * FROM history_events WHERE identifier = :id"),
        {'id': identifier}
    )
    row = result.fetchone()
    assert row is not None
    assert row[1] == 'test_event_1'  # event_identifier
    assert row[3] == 1640000000  # timestamp
    assert row[6] == 'ETH'  # asset


@pytest.mark.asyncio
async def test_add_history_event_with_mapping(async_session: AsyncSession):
    """Test adding a history event with mapping values."""
    # Insert event
    result = await async_session.execute(text("""
        INSERT INTO history_events (
            event_identifier, sequence_index, timestamp, location,
            asset, amount, usd_value, type, subtype, entry_type
        ) VALUES (
            'test_2', 0, 1640000000, 'kraken',
            'BTC', '0.1', '5000.0', 'trade', 'receive', 1
        ) RETURNING identifier
    """))
    
    event_id = result.scalar()
    
    # Add mapping
    await async_session.execute(text("""
        INSERT INTO history_events_mappings (parent_identifier, name, value)
        VALUES (:id, :name, :value)
    """), {'id': event_id, 'name': 'customized', 'value': 1})
    
    await async_session.commit()
    
    # Verify mapping exists
    result = await async_session.execute(
        text("SELECT * FROM history_events_mappings WHERE parent_identifier = :id"),
        {'id': event_id}
    )
    row = result.fetchone()
    assert row is not None
    assert row[1] == 'customized'
    assert row[2] == 1


@pytest.mark.asyncio
async def test_delete_history_events(async_session: AsyncSession):
    """Test deleting history events."""
    # Insert multiple events
    ids = []
    for i in range(3):
        result = await async_session.execute(text("""
            INSERT INTO history_events (
                event_identifier, sequence_index, timestamp, location,
                asset, amount, usd_value, type, entry_type
            ) VALUES (
                :event_id, :seq, 1640000000, 'kraken',
                'ETH', '1.0', '3000.0', 'trade', 1
            ) RETURNING identifier
        """), {'event_id': f'delete_test_{i}', 'seq': i})
        ids.append(result.scalar())
    
    await async_session.commit()
    
    # Delete events
    placeholders = ','.join([f':id{i}' for i in range(len(ids))])
    params = {f'id{i}': id_val for i, id_val in enumerate(ids)}
    await async_session.execute(
        text(f"DELETE FROM history_events WHERE identifier IN ({placeholders})"),
        params
    )
    await async_session.commit()
    
    # Verify deletion
    result = await async_session.execute(
        text("SELECT COUNT(*) FROM history_events WHERE event_identifier LIKE 'delete_test_%'")
    )
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_query_history_events(async_session: AsyncSession):
    """Test querying history events with filters."""
    # Insert test data
    events_data = [
        ('trade_1', 0, 'kraken', 'ETH', 'trade', 'spend'),
        ('trade_2', 0, 'kraken', 'BTC', 'trade', 'receive'),
        ('deposit_1', 0, 'binance', 'USDT', 'deposit', None),
        ('trade_3', 0, 'binance', 'ETH', 'trade', 'spend'),
    ]
    
    for event_id, seq, loc, asset, type_, subtype in events_data:
        await async_session.execute(text("""
            INSERT INTO history_events (
                event_identifier, sequence_index, timestamp, location,
                asset, amount, usd_value, type, subtype, entry_type
            ) VALUES (
                :event_id, :seq, 1640000000, :loc,
                :asset, '1.0', '1000.0', :type, :subtype, 1
            )
        """), {
            'event_id': event_id,
            'seq': seq,
            'loc': loc,
            'asset': asset,
            'type': type_,
            'subtype': subtype,
        })
    
    await async_session.commit()
    
    # Query by location
    result = await async_session.execute(
        text("SELECT COUNT(*) FROM history_events WHERE location = 'kraken'")
    )
    assert result.scalar() == 2
    
    # Query by type
    result = await async_session.execute(
        text("SELECT COUNT(*) FROM history_events WHERE type = 'trade'")
    )
    assert result.scalar() == 3
    
    # Query by asset
    result = await async_session.execute(
        text("SELECT COUNT(*) FROM history_events WHERE asset = 'ETH'")
    )
    assert result.scalar() == 2


@pytest.mark.asyncio
async def test_update_history_event(async_session: AsyncSession):
    """Test updating a history event."""
    # Insert event
    result = await async_session.execute(text("""
        INSERT INTO history_events (
            event_identifier, sequence_index, timestamp, location,
            asset, amount, usd_value, type, entry_type
        ) VALUES (
            'update_test', 0, 1640000000, 'kraken',
            'ETH', '1.0', '3000.0', 'trade', 1
        ) RETURNING identifier
    """))
    
    event_id = result.scalar()
    await async_session.commit()
    
    # Update event
    await async_session.execute(text("""
        UPDATE history_events
        SET amount = '2.0', usd_value = '6000.0', notes = 'Updated'
        WHERE identifier = :id
    """), {'id': event_id})
    
    # Mark as customized
    await async_session.execute(text("""
        INSERT INTO history_events_mappings (parent_identifier, name, value)
        VALUES (:id, 'customized', 1)
        ON CONFLICT(parent_identifier, name) DO UPDATE SET value = 1
    """), {'id': event_id})
    
    await async_session.commit()
    
    # Verify update
    result = await async_session.execute(
        text("SELECT amount, usd_value, notes FROM history_events WHERE identifier = :id"),
        {'id': event_id}
    )
    row = result.fetchone()
    assert row[0] == '2.0'
    assert row[1] == '6000.0'
    assert row[2] == 'Updated'
    
    # Verify customized flag
    result = await async_session.execute(
        text("SELECT value FROM history_events_mappings WHERE parent_identifier = :id AND name = 'customized'"),
        {'id': event_id}
    )
    assert result.scalar() == 1