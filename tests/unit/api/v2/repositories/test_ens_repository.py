"""Tests for ENS repository."""
import pytest
from sqlmodel import Session, create_engine

from rotkehlchen.api.v2.repositories.ens import ENSRepository
from rotkehlchen.db.models.user.base import Base
from rotkehlchen.db.models.user.ens import ENSMapping
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import ChecksumEvmAddress, EnsMapping, Timestamp
from rotkehlchen.utils.misc import ts_now


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def ens_repo(in_memory_db):
    """Create ENS repository with test database."""
    return ENSRepository(in_memory_db)


def test_add_ens_mapping_new(ens_repo, in_memory_db):
    """Test adding a new ENS mapping."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'vitalik.eth'
    now = ts_now()

    # Add mapping
    mapping = ens_repo.add_ens_mapping(address, name, now)

    # Verify it was added
    assert mapping.address == address
    assert mapping.ens_name == name
    assert mapping.last_update == now
    assert mapping.last_avatar_update == 0

    # Check it's in the database
    stored = in_memory_db.get(ENSMapping, address)
    assert stored is not None
    assert stored.ens_name == name


def test_add_ens_mapping_update_existing(ens_repo, in_memory_db):
    """Test updating an existing ENS mapping."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    old_name = 'old.eth'
    new_name = 'new.eth'
    old_time = Timestamp(1000)
    new_time = Timestamp(2000)

    # Add initial mapping
    ens_repo.add_ens_mapping(address, old_name, old_time)

    # Update mapping
    updated = ens_repo.add_ens_mapping(address, new_name, new_time)

    # Verify it was updated
    assert updated.ens_name == new_name
    assert updated.last_update == new_time

    # Check there's still only one entry
    all_mappings = list(in_memory_db.query(ENSMapping).all())
    assert len(all_mappings) == 1


def test_add_ens_mapping_none_name(ens_repo, in_memory_db):
    """Test adding a mapping with None name (checked but no name found)."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')

    # Add mapping with None name
    mapping = ens_repo.add_ens_mapping(address, None)

    # Verify it was added
    assert mapping.address == address
    assert mapping.ens_name is None


def test_get_reverse_ens_with_names(ens_repo):
    """Test getting reverse ENS mappings for addresses with names."""
    addr1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    addr2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
    name1 = 'alice.eth'
    name2 = 'bob.eth'
    time1 = Timestamp(1000)
    time2 = Timestamp(2000)

    # Add mappings
    ens_repo.add_ens_mapping(addr1, name1, time1)
    ens_repo.add_ens_mapping(addr2, name2, time2)

    # Get reverse mappings
    result = ens_repo.get_reverse_ens([addr1, addr2])

    # Verify results
    assert len(result) == 2
    assert isinstance(result[addr1], EnsMapping)
    assert result[addr1].name == name1
    assert result[addr1].last_update == time1
    assert isinstance(result[addr2], EnsMapping)
    assert result[addr2].name == name2
    assert result[addr2].last_update == time2


def test_get_reverse_ens_with_none_names(ens_repo):
    """Test getting reverse ENS mappings for addresses without names."""
    addr = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    time = Timestamp(1000)

    # Add mapping with None name
    ens_repo.add_ens_mapping(addr, None, time)

    # Get reverse mapping
    result = ens_repo.get_reverse_ens([addr])

    # For None names, should return timestamp
    assert len(result) == 1
    assert result[addr] == time


def test_get_reverse_ens_not_found(ens_repo):
    """Test getting reverse ENS for addresses not in database."""
    addr = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')

    # Get reverse mapping for non-existent address
    result = ens_repo.get_reverse_ens([addr])

    # Should return empty dict
    assert result == {}


def test_get_address_for_name_found(ens_repo):
    """Test getting address for an ENS name that exists."""
    addr = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'vitalik.eth'

    # Add mapping
    ens_repo.add_ens_mapping(addr, name)

    # Get address for name
    result = ens_repo.get_address_for_name(name)

    assert result == addr


def test_get_address_for_name_not_found(ens_repo):
    """Test getting address for an ENS name that doesn't exist."""
    result = ens_repo.get_address_for_name('nonexistent.eth')
    assert result is None


def test_update_values(ens_repo):
    """Test bulk updating ENS values."""
    addr1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    addr2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
    addr3 = ChecksumEvmAddress('0x5e349eca2dc61aBCd9dD99Ce94d04136151a09Ee')

    # Set up initial state
    ens_repo.add_ens_mapping(addr1, 'old.eth')

    # Update values
    ens_lookup_results = {
        addr1: 'new.eth',  # Update existing
        addr2: 'alice.eth',  # Add new
        addr3: None,  # Checked but no name
    }
    mappings_to_send = {}

    result = ens_repo.update_values(ens_lookup_results, mappings_to_send)

    # Verify results
    assert result == {
        addr1: 'new.eth',
        addr2: 'alice.eth',
        # addr3 not included because name is None
    }

    # Verify database state
    assert ens_repo.get_address_for_name('new.eth') == addr1
    assert ens_repo.get_address_for_name('alice.eth') == addr2
    assert ens_repo.get_address_for_name('old.eth') is None  # Old mapping removed


def test_update_values_name_conflict(ens_repo):
    """Test updating values when name already belongs to another address."""
    addr1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    addr2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
    name = 'vitalik.eth'

    # Set up initial state - addr1 owns the name
    ens_repo.add_ens_mapping(addr1, name)

    # Try to assign same name to addr2
    ens_lookup_results = {addr2: name}
    mappings_to_send = {}

    result = ens_repo.update_values(ens_lookup_results, mappings_to_send)

    # Verify addr2 now owns the name
    assert result == {addr2: name}
    assert ens_repo.get_address_for_name(name) == addr2

    # Verify addr1 no longer has the name
    reverse = ens_repo.get_reverse_ens([addr1])
    assert addr1 not in reverse  # addr1 was removed completely


def test_get_last_avatar_update(ens_repo):
    """Test getting last avatar update timestamp."""
    addr = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'vitalik.eth'

    # Add mapping
    mapping = ens_repo.add_ens_mapping(addr, name)

    # Get last avatar update
    result = ens_repo.get_last_avatar_update(name)
    assert result == Timestamp(0)  # Default value

    # Update avatar timestamp
    mapping.last_avatar_update = 12345
    ens_repo.session.add(mapping)
    ens_repo.session.commit()

    # Check again
    result = ens_repo.get_last_avatar_update(name)
    assert result == Timestamp(12345)


def test_get_last_avatar_update_not_found(ens_repo):
    """Test getting last avatar update for non-existent name."""
    with pytest.raises(InputError, match='ens name nonexistent.eth is not being tracked'):
        ens_repo.get_last_avatar_update('nonexistent.eth')


def test_find_by(ens_repo):
    """Test finding ENS mappings by criteria."""
    addr1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    addr2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')

    # Add mappings
    ens_repo.add_ens_mapping(addr1, 'alice.eth')
    ens_repo.add_ens_mapping(addr2, 'bob.eth')

    # Find by ens_name
    results = ens_repo.find_by(ens_name='alice.eth')
    assert len(results) == 1
    assert results[0].address == addr1

    # Find by address
    results = ens_repo.find_by(address=addr2)
    assert len(results) == 1
    assert results[0].ens_name == 'bob.eth'
