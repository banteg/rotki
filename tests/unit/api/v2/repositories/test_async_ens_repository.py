"""Tests for async ENS repository."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from rotkehlchen.api.v2.repositories.async_ens import AsyncENSRepository
from rotkehlchen.db.models.user.ens import ENSMapping
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import ChecksumEvmAddress, EnsMapping, Timestamp
from rotkehlchen.utils.misc import ts_now


@pytest_asyncio.fixture
async def async_in_memory_db():
    """Create an async in-memory SQLite database for testing."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')

    # Create only the ENS table
    async with engine.begin() as conn:
        await conn.run_sync(ENSMapping.__table__.create)

    async with AsyncSession(engine) as session:
        yield session
        await session.close()

    await engine.dispose()


@pytest_asyncio.fixture
async def async_ens_repo(async_in_memory_db):
    """Create async ENS repository with test database."""
    return AsyncENSRepository(async_in_memory_db)


@pytest.mark.asyncio
async def test_add_ens_mapping_new(async_ens_repo, async_in_memory_db):
    """Test adding a new ENS mapping."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'vitalik.eth'
    now = ts_now()

    # Add mapping
    mapping = await async_ens_repo.add_ens_mapping(address, name, now)

    # Verify it was added
    assert mapping.address == address
    assert mapping.ens_name == name
    assert mapping.last_update == now
    assert mapping.last_avatar_update == 0

    # Check it's in the database
    stored = await async_in_memory_db.get(ENSMapping, address)
    assert stored is not None
    assert stored.ens_name == name


@pytest.mark.asyncio
async def test_add_ens_mapping_update_existing(async_ens_repo, async_in_memory_db):
    """Test updating an existing ENS mapping."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    old_name = 'old.eth'
    new_name = 'new.eth'
    old_time = Timestamp(1000)
    new_time = Timestamp(2000)

    # Add initial mapping
    await async_ens_repo.add_ens_mapping(address, old_name, old_time)

    # Update mapping
    updated = await async_ens_repo.add_ens_mapping(address, new_name, new_time)

    # Verify update
    assert updated.address == address
    assert updated.ens_name == new_name
    assert updated.last_update == new_time

    # Check database has only one entry
    stored = await async_in_memory_db.get(ENSMapping, address)
    assert stored is not None
    assert stored.ens_name == new_name
    assert stored.last_update == new_time


@pytest.mark.asyncio
async def test_add_ens_mapping_none_name(async_ens_repo, async_in_memory_db):
    """Test adding an ENS mapping with None name (no ENS name)."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    now = ts_now()

    # Add mapping with None name
    mapping = await async_ens_repo.add_ens_mapping(address, None, now)

    # Verify
    assert mapping.address == address
    assert mapping.ens_name is None
    assert mapping.last_update == now


@pytest.mark.asyncio
async def test_get_reverse_ens_with_names(async_ens_repo):
    """Test getting reverse ENS mappings for addresses with names."""
    # Setup test data
    addr1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    addr2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
    addr3 = ChecksumEvmAddress('0x5e349eca2dc61aBCd9dD99Ce94d04136151a09Ee')

    time1 = Timestamp(1000)
    time2 = Timestamp(2000)
    time3 = Timestamp(3000)

    await async_ens_repo.add_ens_mapping(addr1, 'alice.eth', time1)
    await async_ens_repo.add_ens_mapping(addr2, 'bob.eth', time2)
    await async_ens_repo.add_ens_mapping(addr3, None, time3)  # No ENS name

    # Query reverse ENS
    result = await async_ens_repo.get_reverse_ens([addr1, addr2, addr3])

    # Verify results
    assert len(result) == 3

    # addr1 should have ENS mapping
    assert addr1 in result
    assert isinstance(result[addr1], EnsMapping)
    assert result[addr1].name == 'alice.eth'
    assert result[addr1].address == addr1
    assert result[addr1].last_update == time1

    # addr2 should have ENS mapping
    assert addr2 in result
    assert isinstance(result[addr2], EnsMapping)
    assert result[addr2].name == 'bob.eth'

    # addr3 should have timestamp only (no name)
    assert addr3 in result
    assert isinstance(result[addr3], Timestamp)
    assert result[addr3] == time3


@pytest.mark.asyncio
async def test_get_reverse_ens_empty_list(async_ens_repo):
    """Test getting reverse ENS with empty address list."""
    result = await async_ens_repo.get_reverse_ens([])
    assert result == {}


@pytest.mark.asyncio
async def test_get_reverse_ens_no_matches(async_ens_repo):
    """Test getting reverse ENS for addresses not in database."""
    addr = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    result = await async_ens_repo.get_reverse_ens([addr])
    assert result == {}


@pytest.mark.asyncio
async def test_get_address_for_name(async_ens_repo):
    """Test getting address for ENS name."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'vitalik.eth'

    # Add mapping
    await async_ens_repo.add_ens_mapping(address, name)

    # Get address for name
    found_address = await async_ens_repo.get_address_for_name(name)
    assert found_address == address


@pytest.mark.asyncio
async def test_get_address_for_name_not_found(async_ens_repo):
    """Test getting address for non-existent ENS name."""
    result = await async_ens_repo.get_address_for_name('notfound.eth')
    assert result is None


@pytest.mark.asyncio
async def test_update_values(async_ens_repo):
    """Test updating multiple ENS values."""
    addr1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    addr2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')

    # Add initial mapping for addr1
    await async_ens_repo.add_ens_mapping(addr1, 'old.eth')

    # Update values
    ens_lookup_results = {
        addr1: 'new.eth',  # Update existing
        addr2: 'bob.eth',  # Add new
    }
    mappings_to_send = {}

    result = await async_ens_repo.update_values(ens_lookup_results, mappings_to_send)

    # Verify results
    assert result == {
        addr1: 'new.eth',
        addr2: 'bob.eth',
    }

    # Verify database updates
    mapping1 = await async_ens_repo.get_address_for_name('new.eth')
    assert mapping1 == addr1

    mapping2 = await async_ens_repo.get_address_for_name('bob.eth')
    assert mapping2 == addr2

    # Old name should not exist
    old_mapping = await async_ens_repo.get_address_for_name('old.eth')
    assert old_mapping is None


@pytest.mark.asyncio
async def test_update_values_with_conflicts(async_ens_repo):
    """Test updating values when ENS name conflicts with another address."""
    addr1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    addr2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')

    # Add initial mapping
    await async_ens_repo.add_ens_mapping(addr1, 'alice.eth')

    # Try to assign same name to different address
    ens_lookup_results = {
        addr2: 'alice.eth',  # This should remove addr1's mapping
    }
    mappings_to_send = {}

    result = await async_ens_repo.update_values(ens_lookup_results, mappings_to_send)

    # Verify results
    assert result == {addr2: 'alice.eth'}

    # Verify addr2 now has the name
    current_addr = await async_ens_repo.get_address_for_name('alice.eth')
    assert current_addr == addr2

    # Verify addr1 no longer has the name
    reverse_lookup = await async_ens_repo.get_reverse_ens([addr1])
    if addr1 in reverse_lookup:
        # If addr1 is still in DB, it should have no name
        assert isinstance(reverse_lookup[addr1], Timestamp)


@pytest.mark.asyncio
async def test_get_last_avatar_update(async_ens_repo):
    """Test getting last avatar update time."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'vitalik.eth'

    # Add mapping
    await async_ens_repo.add_ens_mapping(address, name)

    # Get avatar update time (should be 0 by default)
    update_time = await async_ens_repo.get_last_avatar_update(name)
    assert update_time == Timestamp(0)


@pytest.mark.asyncio
async def test_get_last_avatar_update_not_found(async_ens_repo):
    """Test getting avatar update time for non-existent ENS name."""
    with pytest.raises(InputError, match='ens name notfound.eth is not being tracked'):
        await async_ens_repo.get_last_avatar_update('notfound.eth')


@pytest.mark.asyncio
async def test_find_by(async_ens_repo):
    """Test finding ENS mappings by criteria."""
    # Add test data
    addr1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    addr2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')

    await async_ens_repo.add_ens_mapping(addr1, 'alice.eth')
    await async_ens_repo.add_ens_mapping(addr2, 'bob.eth')

    # Find by name
    results = await async_ens_repo.find_by(ens_name='alice.eth')
    assert len(results) == 1
    assert results[0].address == addr1

    # Find by address
    results = await async_ens_repo.find_by(address=addr2)
    assert len(results) == 1
    assert results[0].ens_name == 'bob.eth'
