"""Tests for async AddressBook repository."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from rotkehlchen.api.v2.repositories.async_addressbook import AsyncAddressBookRepository
from rotkehlchen.db.models.user.address_book import AddressBook
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import (
    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
    AddressbookEntry,
    ChecksumEvmAddress,
    OptionalChainAddress,
    SupportedBlockchain,
)


@pytest_asyncio.fixture
async def async_in_memory_db():
    """Create an async in-memory SQLite database for testing."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    
    # Create only the AddressBook table
    async with engine.begin() as conn:
        await conn.run_sync(AddressBook.__table__.create)
    
    async with AsyncSession(engine) as session:
        yield session
        await session.close()
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_addressbook_repo(async_in_memory_db):
    """Create async AddressBook repository with test database."""
    return AsyncAddressBookRepository(async_in_memory_db)


@pytest.mark.asyncio
async def test_add_addressbook_entry_simple(async_addressbook_repo):
    """Test adding a simple addressbook entry."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'Alice'
    blockchain = SupportedBlockchain.ETHEREUM
    
    entry = AddressbookEntry(
        address=address,
        name=name,
        blockchain=blockchain,
    )
    
    await async_addressbook_repo.add_or_update_addressbook_entries([entry])
    
    # Verify it was added
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 1
    assert results[0].name == name
    assert results[0].blockchain == blockchain.value


@pytest.mark.asyncio
async def test_add_addressbook_entry_multichain(async_addressbook_repo):
    """Test adding a multichain addressbook entry (blockchain=None)."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'Bob'
    
    entry = AddressbookEntry(
        address=address,
        name=name,
        blockchain=None,  # Multichain
    )
    
    await async_addressbook_repo.add_or_update_addressbook_entries([entry])
    
    # Verify it was added with ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 1
    assert results[0].name == name
    assert results[0].blockchain == ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE


@pytest.mark.asyncio
async def test_update_addressbook_entry(async_addressbook_repo):
    """Test updating an existing addressbook entry."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    old_name = 'Old Name'
    new_name = 'New Name'
    blockchain = SupportedBlockchain.ETHEREUM
    
    # Add initial entry
    entry = AddressbookEntry(address=address, name=old_name, blockchain=blockchain)
    await async_addressbook_repo.add_or_update_addressbook_entries([entry])
    
    # Update the entry
    updated_entry = AddressbookEntry(address=address, name=new_name, blockchain=blockchain)
    await async_addressbook_repo.add_or_update_addressbook_entries([updated_entry])
    
    # Verify update
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 1
    assert results[0].name == new_name


@pytest.mark.asyncio
async def test_delete_addressbook_entry_with_blockchain(async_addressbook_repo):
    """Test deleting an addressbook entry with specific blockchain."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'To Delete'
    blockchain = SupportedBlockchain.ETHEREUM
    
    # Add entry
    entry = AddressbookEntry(address=address, name=name, blockchain=blockchain)
    await async_addressbook_repo.add_or_update_addressbook_entries([entry])
    
    # Delete it
    chain_address = OptionalChainAddress(address=address, blockchain=blockchain)
    await async_addressbook_repo.delete_addressbook_entries([chain_address])
    
    # Verify deletion
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_delete_addressbook_entry_all_chains(async_addressbook_repo):
    """Test deleting all addressbook entries for an address."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    
    # Add entries for multiple chains
    entries = [
        AddressbookEntry(address=address, name='ETH', blockchain=SupportedBlockchain.ETHEREUM),
        AddressbookEntry(address=address, name='BSC', blockchain=SupportedBlockchain.BINANCE),
        AddressbookEntry(address=address, name='MATIC', blockchain=SupportedBlockchain.POLYGON),
    ]
    await async_addressbook_repo.add_or_update_addressbook_entries(entries)
    
    # Delete all entries for this address
    chain_address = OptionalChainAddress(address=address, blockchain=None)
    await async_addressbook_repo.delete_addressbook_entries([chain_address])
    
    # Verify all were deleted
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_delete_non_existent_entry_raises_error(async_addressbook_repo):
    """Test that deleting non-existent entry raises error."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    
    chain_address = OptionalChainAddress(address=address, blockchain=None)
    
    with pytest.raises(InputError, match='are not present in the database'):
        await async_addressbook_repo.delete_addressbook_entries([chain_address])


@pytest.mark.asyncio
async def test_get_addressbook_entry_name_exact_match(async_addressbook_repo):
    """Test getting name for exact blockchain match."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'Exact Match'
    blockchain = SupportedBlockchain.ETHEREUM
    
    # Add entry
    entry = AddressbookEntry(address=address, name=name, blockchain=blockchain)
    await async_addressbook_repo.add_or_update_addressbook_entries([entry])
    
    # Get name
    chain_address = OptionalChainAddress(address=address, blockchain=blockchain)
    found_name = await async_addressbook_repo.get_addressbook_entry_name(chain_address)
    assert found_name == name


@pytest.mark.asyncio
async def test_get_addressbook_entry_name_multichain_fallback(async_addressbook_repo):
    """Test getting name falls back to multichain entry."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'Multichain'
    
    # Add multichain entry
    entry = AddressbookEntry(address=address, name=name, blockchain=None)
    await async_addressbook_repo.add_or_update_addressbook_entries([entry])
    
    # Try to get name for specific blockchain
    chain_address = OptionalChainAddress(address=address, blockchain=SupportedBlockchain.ETHEREUM)
    found_name = await async_addressbook_repo.get_addressbook_entry_name(chain_address)
    assert found_name == name


@pytest.mark.asyncio
async def test_get_addressbook_entry_name_not_found(async_addressbook_repo):
    """Test getting name for non-existent entry returns None."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    
    chain_address = OptionalChainAddress(address=address, blockchain=SupportedBlockchain.ETHEREUM)
    found_name = await async_addressbook_repo.get_addressbook_entry_name(chain_address)
    assert found_name is None


@pytest.mark.asyncio
async def test_update_entry_delete_with_empty_name(async_addressbook_repo):
    """Test that updating entry with empty name deletes it."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'To Be Deleted'
    blockchain = SupportedBlockchain.ETHEREUM
    
    # Add entry
    entry = AddressbookEntry(address=address, name=name, blockchain=blockchain)
    await async_addressbook_repo.add_or_update_addressbook_entries([entry])
    
    # Update with empty name (should delete)
    delete_entry = AddressbookEntry(address=address, name='', blockchain=blockchain)
    await async_addressbook_repo.update_addressbook_entries([delete_entry])
    
    # Verify deletion
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_update_non_existent_entry_with_empty_name_raises_error(async_addressbook_repo):
    """Test that updating non-existent entry with empty name raises error."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    blockchain = SupportedBlockchain.ETHEREUM
    
    delete_entry = AddressbookEntry(address=address, name='', blockchain=blockchain)
    
    with pytest.raises(InputError, match="doesn't exist in the address book"):
        await async_addressbook_repo.update_addressbook_entries([delete_entry])


@pytest.mark.asyncio
async def test_maybe_make_entry_name_multichain_same_names(async_addressbook_repo):
    """Test making entry multichain when all chains have same name."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    name = 'Same Name'
    
    # Add entries with same name for multiple chains
    entries = [
        AddressbookEntry(address=address, name=name, blockchain=SupportedBlockchain.ETHEREUM),
        AddressbookEntry(address=address, name=name, blockchain=SupportedBlockchain.BINANCE),
        AddressbookEntry(address=address, name=name, blockchain=SupportedBlockchain.POLYGON),
    ]
    await async_addressbook_repo.add_or_update_addressbook_entries(entries)
    
    # Make multichain
    await async_addressbook_repo.maybe_make_entry_name_multichain(address)
    
    # Verify single multichain entry exists
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 1
    assert results[0].name == name
    assert results[0].blockchain == ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE


@pytest.mark.asyncio
async def test_maybe_make_entry_name_multichain_different_names(async_addressbook_repo):
    """Test that multichain conversion doesn't happen with different names."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    
    # Add entries with different names
    entries = [
        AddressbookEntry(address=address, name='ETH Name', blockchain=SupportedBlockchain.ETHEREUM),
        AddressbookEntry(address=address, name='BSC Name', blockchain=SupportedBlockchain.BINANCE),
    ]
    await async_addressbook_repo.add_or_update_addressbook_entries(entries)
    
    # Try to make multichain
    await async_addressbook_repo.maybe_make_entry_name_multichain(address)
    
    # Verify entries remain separate
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {'ETH Name', 'BSC Name'}


@pytest.mark.asyncio
async def test_multichain_entry_removes_blockchain_specific_entries(async_addressbook_repo):
    """Test that adding multichain entry removes blockchain-specific entries."""
    address = ChecksumEvmAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    
    # Add blockchain-specific entries
    entries = [
        AddressbookEntry(address=address, name='ETH', blockchain=SupportedBlockchain.ETHEREUM),
        AddressbookEntry(address=address, name='BSC', blockchain=SupportedBlockchain.BINANCE),
    ]
    await async_addressbook_repo.add_or_update_addressbook_entries(entries)
    
    # Add multichain entry
    multichain_entry = AddressbookEntry(address=address, name='All Chains', blockchain=None)
    await async_addressbook_repo.add_or_update_addressbook_entries([multichain_entry])
    
    # Verify only multichain entry remains
    results = await async_addressbook_repo.find_by(address=address)
    assert len(results) == 1
    assert results[0].name == 'All Chains'
    assert results[0].blockchain == ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE