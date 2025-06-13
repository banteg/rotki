"""Tests for async Loopring repository."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from rotki2.api.v2.repositories.async_loopring import AsyncLoopringRepository
from rotki2.db.models.user.cache import MultiSettings
from rotkehlchen.types import ChecksumEvmAddress


@pytest_asyncio.fixture
async def async_in_memory_db():
    """Create an async in-memory SQLite database for testing."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    
    # Create only the MultiSettings table
    async with engine.begin() as conn:
        await conn.run_sync(MultiSettings.__table__.create)
    
    async with AsyncSession(engine) as session:
        yield session
        await session.close()
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_loopring_repo(async_in_memory_db):
    """Create async Loopring repository with test database."""
    return AsyncLoopringRepository(async_in_memory_db)


@pytest.mark.asyncio
async def test_add_accountid_mapping(async_loopring_repo):
    """Test adding a Loopring account ID mapping."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    account_id = 12345
    
    # Add mapping
    await async_loopring_repo.add_accountid_mapping(address, account_id)
    
    # Verify it was added
    retrieved_id = await async_loopring_repo.get_accountid_mapping(address)
    assert retrieved_id == account_id


@pytest.mark.asyncio
async def test_add_accountid_mapping_duplicate(async_loopring_repo):
    """Test adding duplicate account ID mapping doesn't create duplicates."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    account_id = 12345
    
    # Add mapping twice
    await async_loopring_repo.add_accountid_mapping(address, account_id)
    await async_loopring_repo.add_accountid_mapping(address, account_id)
    
    # Verify only one exists
    mappings = await async_loopring_repo.find_by()
    assert len(mappings) == 1


@pytest.mark.asyncio
async def test_remove_accountid_mapping(async_loopring_repo):
    """Test removing a Loopring account ID mapping."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    account_id = 12345
    
    # Add mapping
    await async_loopring_repo.add_accountid_mapping(address, account_id)
    
    # Remove it
    await async_loopring_repo.remove_accountid_mapping(address)
    
    # Verify it's gone
    retrieved_id = await async_loopring_repo.get_accountid_mapping(address)
    assert retrieved_id is None


@pytest.mark.asyncio
async def test_remove_non_existent_mapping(async_loopring_repo):
    """Test removing non-existent mapping doesn't raise error."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    
    # Remove non-existent mapping (should not raise)
    await async_loopring_repo.remove_accountid_mapping(address)
    
    # Verify nothing was affected
    mappings = await async_loopring_repo.find_by()
    assert len(mappings) == 0


@pytest.mark.asyncio
async def test_get_accountid_mapping_not_found(async_loopring_repo):
    """Test getting account ID for non-existent mapping returns None."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    
    # Get non-existent mapping
    account_id = await async_loopring_repo.get_accountid_mapping(address)
    assert account_id is None


@pytest.mark.asyncio
async def test_multiple_account_mappings(async_loopring_repo):
    """Test managing multiple account mappings."""
    address1 = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    address2 = ChecksumEvmAddress('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
    address3 = ChecksumEvmAddress('0x5e349eca2dc61aBCd9dD99Ce94d04136151a09Ee')
    
    account_id1 = 10001
    account_id2 = 10002
    account_id3 = 10003
    
    # Add multiple mappings
    await async_loopring_repo.add_accountid_mapping(address1, account_id1)
    await async_loopring_repo.add_accountid_mapping(address2, account_id2)
    await async_loopring_repo.add_accountid_mapping(address3, account_id3)
    
    # Verify all mappings
    assert await async_loopring_repo.get_accountid_mapping(address1) == account_id1
    assert await async_loopring_repo.get_accountid_mapping(address2) == account_id2
    assert await async_loopring_repo.get_accountid_mapping(address3) == account_id3
    
    # Verify total count
    mappings = await async_loopring_repo.find_by()
    assert len(mappings) == 3


@pytest.mark.asyncio
async def test_update_account_mapping(async_loopring_repo):
    """Test updating an existing account mapping."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    old_account_id = 10001
    new_account_id = 20002
    
    # Add initial mapping
    await async_loopring_repo.add_accountid_mapping(address, old_account_id)
    
    # Remove old and add new (since we can't update directly)
    await async_loopring_repo.remove_accountid_mapping(address)
    await async_loopring_repo.add_accountid_mapping(address, new_account_id)
    
    # Verify update
    assert await async_loopring_repo.get_accountid_mapping(address) == new_account_id


@pytest.mark.asyncio
async def test_find_by_filters_loopring_only(async_loopring_repo, async_in_memory_db):
    """Test that find_by only returns Loopring-related entries."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    account_id = 12345
    
    # Add Loopring mapping
    await async_loopring_repo.add_accountid_mapping(address, account_id)
    
    # Add non-Loopring entry directly
    other_setting = MultiSettings(name='other_setting', value='other_value')
    async_in_memory_db.add(other_setting)
    await async_in_memory_db.commit()
    
    # Find should only return Loopring entries
    loopring_mappings = await async_loopring_repo.find_by()
    assert len(loopring_mappings) == 1
    assert loopring_mappings[0].name.startswith('loopring_')