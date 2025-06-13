"""Tests for History repository."""
import pytest
from sqlmodel import Session, create_engine

from rotki2.api.v2.repositories.history import HistoryEventFilter, HistoryRepository
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotki2.db.models.user.base import Base
from rotki2.db.models.user.history import (
    EvmEventInfo,
    HistoryEvent,
    HistoryEventMapping,
)
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.types import Location, Timestamp


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def history_repo(in_memory_db):
    """Create History repository with test database."""
    return HistoryRepository(in_memory_db)


@pytest.fixture
def sample_events(in_memory_db):
    """Create sample history events for testing."""
    events = []

    # Create regular history events
    for i in range(5):
        event = HistoryEvent(
            identifier=i + 1,
            entry_type=HistoryBaseEntryType.HISTORY_EVENT.serialize_for_db(),
            event_identifier=f'event_{i}',
            sequence_index=0,
            timestamp=1000 + i * 100,
            location=Location.ETHEREUM.serialize_for_db(),
            location_label=f"0x{'0' * 38}{i:02x}",
            asset='ETH',
            amount='1.0',
            notes=f'Test event {i}',
            type='trade',
            subtype='buy',
            ignored=0,
        )
        in_memory_db.add(event)
        events.append(event)

    # Create EVM events
    for i in range(5, 8):
        event = HistoryEvent(
            identifier=i + 1,
            entry_type=HistoryBaseEntryType.EVM_EVENT.serialize_for_db(),
            event_identifier=f"0x{'a' * 62}{i:02x}",
            sequence_index=0,
            timestamp=1500 + i * 100,
            location=Location.ETHEREUM.serialize_for_db(),
            asset='USDC',
            amount='100.0',
            notes=f'EVM event {i}',
            type='receive',
            subtype='none',
            ignored=0,
        )
        in_memory_db.add(event)
        events.append(event)

        # Add EVM info
        evm_info = EvmEventInfo(
            identifier=event.identifier,
            tx_hash=bytes.fromhex(f"{'b' * 62}{i:02x}"),
            counterparty='Uniswap',
            product='Pool',
            address=f"0x{'c' * 38}{i:02x}",
        )
        in_memory_db.add(evm_info)

    in_memory_db.commit()
    return events


def test_get_history_events_basic(history_repo, sample_events):
    """Test basic retrieval of history events."""
    filters = HistoryEventFilter()
    events = history_repo.get_history_events(filters)

    assert len(events) == 8
    # Should be ordered by timestamp ascending by default
    assert events[0].timestamp < events[-1].timestamp


def test_get_history_events_with_timestamp_filter(history_repo, sample_events):
    """Test filtering events by timestamp range."""
    filters = HistoryEventFilter(
        from_ts=Timestamp(1200),
        to_ts=Timestamp(1600),
    )
    events = history_repo.get_history_events(filters)

    assert len(events) == 4
    for event in events:
        assert 1200 <= event.timestamp <= 1600


def test_get_history_events_with_location_filter(history_repo, sample_events):
    """Test filtering events by location."""
    filters = HistoryEventFilter(
        location=Location.ETHEREUM,
    )
    events = history_repo.get_history_events(filters)

    assert len(events) == 8  # All our sample events are Ethereum


def test_get_history_events_with_asset_filter(history_repo, sample_events):
    """Test filtering events by asset."""
    filters = HistoryEventFilter(
        asset='USDC',
    )
    events = history_repo.get_history_events(filters)

    assert len(events) == 3
    for event in events:
        assert event.asset == 'USDC'


def test_get_history_events_with_type_filter(history_repo, sample_events):
    """Test filtering events by type."""
    filters = HistoryEventFilter(
        event_types=['trade'],
    )
    events = history_repo.get_history_events(filters)

    assert len(events) == 5
    for event in events:
        assert event.type == 'trade'


def test_get_history_events_with_address_filter(history_repo, sample_events):
    """Test filtering events by address."""
    # Test with location_label
    filters = HistoryEventFilter(
        addresses=['0x0000000000000000000000000000000000000001'],
    )
    events = history_repo.get_history_events(filters)

    assert len(events) == 1
    assert events[0].location_label == '0x0000000000000000000000000000000000000001'

    # Test with EVM address
    filters = HistoryEventFilter(
        addresses=['0xcccccccccccccccccccccccccccccccccccccc05'],
    )
    events = history_repo.get_history_events(filters)

    assert len(events) == 1
    assert events[0].identifier == 6


def test_get_history_events_with_tx_hash_filter(history_repo, sample_events):
    """Test filtering events by transaction hash."""
    tx_hash = bytes.fromhex('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb05')
    filters = HistoryEventFilter(
        tx_hashes=[tx_hash],
    )
    events = history_repo.get_history_events(filters)

    assert len(events) == 1
    assert events[0].identifier == 6


def test_get_history_events_with_counterparty_filter(history_repo, sample_events):
    """Test filtering events by counterparty."""
    filters = HistoryEventFilter(
        counterparties=['Uniswap'],
    )
    events = history_repo.get_history_events(filters)

    assert len(events) == 3
    for event in events:
        assert event.identifier in [6, 7, 8]


def test_get_history_events_exclude_ignored(history_repo, sample_events):
    """Test excluding ignored events."""
    # Mark some events as ignored
    sample_events[0].ignored = 1
    sample_events[2].ignored = 1
    history_repo.session.add(sample_events[0])
    history_repo.session.add(sample_events[2])
    history_repo.session.commit()

    filters = HistoryEventFilter(exclude_ignored=True)
    events = history_repo.get_history_events(filters)

    assert len(events) == 6
    for event in events:
        assert event.ignored == 0


def test_get_history_events_with_limit(history_repo, sample_events):
    """Test limiting number of results."""
    filters = HistoryEventFilter()
    events = history_repo.get_history_events(filters, limit=3)

    assert len(events) == 3


def test_get_history_events_with_offset(history_repo, sample_events):
    """Test offset for pagination."""
    filters = HistoryEventFilter()
    events = history_repo.get_history_events(filters, limit=3, offset=2)

    assert len(events) == 3
    assert events[0].identifier == 3


def test_get_history_events_descending_order(history_repo, sample_events):
    """Test getting events in descending order."""
    filters = HistoryEventFilter()
    events = history_repo.get_history_events(filters, ascending=False)

    assert len(events) == 8
    assert events[0].timestamp > events[-1].timestamp


def test_get_history_events_free_user_limit(history_repo, sample_events):
    """Test free user limit is applied."""
    # Add many more events to exceed free limit
    for i in range(8, FREE_HISTORY_EVENTS_LIMIT + 10):
        event = HistoryEvent(
            identifier=i + 1,
            entry_type=HistoryBaseEntryType.HISTORY_EVENT.serialize_for_db(),
            event_identifier=f'event_{i}',
            sequence_index=0,
            timestamp=2000 + i,
            location=Location.ETHEREUM.serialize_for_db(),
            asset='ETH',
            amount='1.0',
            type='trade',
            subtype='buy',
            ignored=0,
        )
        history_repo.session.add(event)
    history_repo.session.commit()

    filters = HistoryEventFilter()
    events = history_repo.get_history_events(filters, has_premium=False)

    assert len(events) == FREE_HISTORY_EVENTS_LIMIT


def test_get_history_events_count(history_repo, sample_events):
    """Test getting count of events."""
    filters = HistoryEventFilter()
    limited_count, total_count = history_repo.get_history_events_count(filters)

    assert total_count == 8
    assert limited_count == 8


def test_add_history_event(history_repo):
    """Test adding a new history event."""
    event = HistoryEvent(
        entry_type=HistoryBaseEntryType.HISTORY_EVENT.serialize_for_db(),
        event_identifier='new_event',
        sequence_index=0,
        timestamp=1234567890,
        location=Location.ETHEREUM.serialize_for_db(),
        asset='ETH',
        amount='1.5',
        type='trade',
        subtype='buy',
        ignored=0,
    )

    identifier = history_repo.add_history_event(event)

    assert identifier is not None
    assert event.identifier == identifier

    # Verify it's in the database
    stored = history_repo.session.get(HistoryEvent, identifier)
    assert stored is not None
    assert stored.event_identifier == 'new_event'


def test_add_history_event_with_mappings(history_repo):
    """Test adding event with mapping values."""
    event = HistoryEvent(
        entry_type=HistoryBaseEntryType.HISTORY_EVENT.serialize_for_db(),
        event_identifier='mapped_event',
        sequence_index=0,
        timestamp=1234567890,
        location=Location.ETHEREUM.serialize_for_db(),
        asset='ETH',
        amount='1.5',
        type='trade',
        subtype='buy',
        ignored=0,
    )

    mapping_values = {
        'custom_field': 42,
        'another_field': 100,
    }

    identifier = history_repo.add_history_event(event, mapping_values)

    # Verify mappings were created
    mappings = history_repo.session.query(HistoryEventMapping).filter_by(
        parent_identifier=identifier,
    ).all()
    assert len(mappings) == 2

    mapping_dict = {m.name: m.value for m in mappings}
    assert mapping_dict['custom_field'] == 42
    assert mapping_dict['another_field'] == 100


def test_edit_history_event(history_repo, sample_events):
    """Test editing an existing history event."""
    event = sample_events[0]
    event.amount = '2.5'
    event.notes = 'Updated notes'

    history_repo.edit_history_event(event)

    # Verify changes were saved
    updated = history_repo.session.get(HistoryEvent, event.identifier)
    assert updated.amount == '2.5'
    assert updated.notes == 'Updated notes'

    # Verify customized mapping was added
    mapping = history_repo.session.query(HistoryEventMapping).filter_by(
        parent_identifier=event.identifier,
        name=HISTORY_MAPPING_KEY_STATE,
        value=HISTORY_MAPPING_STATE_CUSTOMIZED,
    ).first()
    assert mapping is not None


def test_delete_events_by_tx_hash(history_repo, sample_events):
    """Test deleting events by transaction hash."""
    tx_hash = bytes.fromhex('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb05')

    history_repo.delete_events_by_tx_hash(
        tx_hashes=[tx_hash],
        location=Location.ETHEREUM,
    )

    # Verify event was deleted
    event = history_repo.session.get(HistoryEvent, 6)
    assert event is None


def test_delete_events_by_tx_hash_preserve_customized(history_repo, sample_events):
    """Test deleting events preserves customized ones."""
    # Mark an event as customized
    mapping = HistoryEventMapping(
        parent_identifier=6,
        name=HISTORY_MAPPING_KEY_STATE,
        value=HISTORY_MAPPING_STATE_CUSTOMIZED,
    )
    history_repo.session.add(mapping)
    history_repo.session.commit()

    tx_hash = bytes.fromhex('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb05')

    history_repo.delete_events_by_tx_hash(
        tx_hashes=[tx_hash],
        location=Location.ETHEREUM,
        delete_customized=False,
    )

    # Verify customized event was NOT deleted
    event = history_repo.session.get(HistoryEvent, 6)
    assert event is not None


def test_get_customized_event_identifiers(history_repo, sample_events):
    """Test getting identifiers of customized events."""
    # Mark some events as customized
    for i in [1, 3, 5]:
        mapping = HistoryEventMapping(
            parent_identifier=i,
            name=HISTORY_MAPPING_KEY_STATE,
            value=HISTORY_MAPPING_STATE_CUSTOMIZED,
        )
        history_repo.session.add(mapping)
    history_repo.session.commit()

    identifiers = history_repo.get_customized_event_identifiers()

    assert len(identifiers) == 3
    assert set(identifiers) == {1, 3, 5}


def test_find_missing_prices(history_repo):
    """Test finding events with missing USD prices."""
    # Create events with and without prices
    events = []
    for i in range(4):
        event = HistoryEvent(
            identifier=i + 1,
            entry_type=HistoryBaseEntryType.HISTORY_EVENT.serialize_for_db(),
            event_identifier=f'price_event_{i}',
            sequence_index=0,
            timestamp=1000 + i * 100,
            location=Location.ETHEREUM.serialize_for_db(),
            asset=f'TOKEN{i}',
            amount='1.0' if i != 3 else '0',  # Last one has 0 amount
            usd_value='100.0' if i % 2 == 0 else None,  # Even ones have price
            type='trade',
            subtype='buy',
            ignored=0,
        )
        history_repo.session.add(event)
        events.append(event)
    history_repo.session.commit()

    missing = history_repo.find_missing_prices()

    # Should find only event 1 (index 1) - has amount but no price
    # Event 3 has no price but amount is 0, so it's excluded
    assert len(missing) == 1
    assert missing[0] == ('TOKEN1', Timestamp(1100))


def test_find_by_event_identifier(history_repo, sample_events):
    """Test finding events by event identifier."""
    events = history_repo.find_by_event_identifier('event_2')

    assert len(events) == 1
    assert events[0].identifier == 3


def test_find_by_tx_hash(history_repo, sample_events):
    """Test finding events by transaction hash."""
    tx_hash = bytes.fromhex('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb06')
    events = history_repo.find_by_tx_hash(tx_hash)

    assert len(events) == 1
    assert events[0].identifier == 7


def test_find_by_address(history_repo, sample_events):
    """Test finding events by address."""
    # Find by location_label
    events = history_repo.find_by_address('0x0000000000000000000000000000000000000002')
    assert len(events) == 1
    assert events[0].identifier == 3

    # Find by EVM address
    events = history_repo.find_by_address('0xcccccccccccccccccccccccccccccccccccccc06')
    assert len(events) == 1
    assert events[0].identifier == 7
