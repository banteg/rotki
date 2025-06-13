"""Async repository for managing address book entries."""
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from rotkehlchen.api.v2.repositories.async_base import AsyncBaseRepository
from rotkehlchen.db.models.user.address_book import AddressBook
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import (
    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
    AddressbookEntry,
    AddressbookType,
    ChecksumEvmAddress,
    OptionalChainAddress,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.db.filtering import AddressbookFilterQuery


class AsyncAddressBookRepository(AsyncBaseRepository[AddressBook]):
    """Async repository for managing address book entries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AddressBook)

    async def get_addressbook_entries(
        self,
        filter_query: 'AddressbookFilterQuery | None' = None,
    ) -> tuple[list[AddressbookEntry], int]:
        """
        Returns paginated addressbook entries for the given filter.
        If blockchain is None for a given pair, returns all entries for the pair's address.
        """
        # First get total count
        count_query, bindings = filter_query.prepare(with_pagination=False) if filter_query else ('', [])
        count_statement = 'SELECT COUNT(*) FROM address_book ' + count_query
        
        # Execute raw SQL for count
        result = await self.session.execute(count_statement, bindings)
        total_found = result.scalar()

        # Get actual entries
        query, bindings = filter_query.prepare() if filter_query else ('', [])
        query = 'SELECT address, name, blockchain FROM address_book ' + query
        
        result = await self.session.execute(query, bindings)
        entries = [
            AddressbookEntry(
                address=ChecksumEvmAddress(row[0]),
                name=row[1],
                blockchain=SupportedBlockchain(row[2]) if row[2] != ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE else None,
            ) for row in result
        ]
        
        return entries, total_found

    async def add_or_update_addressbook_entries(
        self,
        entries: list[AddressbookEntry],
    ) -> None:
        """Adds new or updates existing addressbook entries.

        If blockchain is None then make sure that the same address doesn't appear in combination
        with other blockchain values.
        """
        for entry in entries:
            # If blockchain is None, delete any other entry for that address
            if entry.blockchain is None:
                statement = select(AddressBook).where(
                    AddressBook.address == entry.address,
                    AddressBook.blockchain != ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
                )
                result = await self.session.execute(statement)
                for row in result:
                    self.session.delete(row[0])
                await self.session.commit()

            # Check if entry exists
            blockchain_value = entry.blockchain.value if entry.blockchain else ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE
            existing = await self.session.get(AddressBook, (entry.address, blockchain_value))
            
            if existing:
                # Update existing
                existing.name = entry.name
                self.session.add(existing)
            else:
                # Create new
                new_entry = AddressBook(
                    address=entry.address,
                    name=entry.name,
                    blockchain=blockchain_value,
                )
                self.session.add(new_entry)
            
            await self.session.commit()

    async def update_addressbook_entries(
        self,
        entries: list[AddressbookEntry],
    ) -> None:
        """Updates names of addressbook entries.
        Add entry if it doesn't exist. Delete entry if the name is blank
        If blockchain is None then make sure that the same address doesn't appear in combination
        with other blockchain values.
        """
        for entry in entries:
            if entry.name == '':  # Handle deletion case
                entry_blockchain_value = (
                    entry.blockchain.value if entry.blockchain
                    else ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE
                )
                
                existing = await self.session.get(AddressBook, (entry.address, entry_blockchain_value))
                if not existing:
                    raise InputError(
                        f'Entry with address "{entry.address}" and blockchain {entry.blockchain} '
                        f"doesn't exist in the address book. So it cannot be modified.",
                    )
                
                self.session.delete(existing)
                await self.session.commit()
            else:  # insert or update
                await self.add_or_update_addressbook_entries([entry])

    async def delete_addressbook_entries(
        self,
        chain_addresses: list[OptionalChainAddress],
    ) -> None:
        """Delete addressbook entries.
        May raise:
        - InputError: if any of the addresses that need to be deleted is not present in the
        addressbook
        """
        # First check that all addresses exist
        addresses = {chain_address.address for chain_address in chain_addresses}
        
        statement = select(AddressBook.address).where(
            AddressBook.address.in_(list(addresses))
        ).distinct()
        result = await self.session.execute(statement)
        db_addresses = {row[0] for row in result}
        
        if len(addresses) != len(db_addresses):
            missing = addresses - db_addresses
            raise InputError(f'Addresses {missing} are not present in the database')

        # Delete entries
        for address, blockchain in chain_addresses:
            if blockchain is not None:
                blockchain_value = blockchain.value
                existing = await self.session.get(AddressBook, (address, blockchain_value))
                if not existing:
                    raise InputError(
                        'One or more of the addresses with blockchains provided do not exist in the database'
                    )
                self.session.delete(existing)
            else:
                # Delete all entries for this address
                statement = select(AddressBook).where(AddressBook.address == address)
                result = await self.session.execute(statement)
                for row in result:
                    self.session.delete(row[0])
        
        await self.session.commit()

    async def get_addressbook_entry_name(
        self,
        chain_address: OptionalChainAddress,
    ) -> str | None:
        """
        Returns the name for the specified address and blockchain.
        It will search for the pair of address and the exact blockchain (or null).
        If it's not found, it will search for the pair of address
        with blockchain=NULL (meaning, for all chains).
        Otherwise, it will return None.
        """
        # First try exact match
        if chain_address.blockchain is not None:
            blockchain_value = chain_address.blockchain.value
            existing = await self.session.get(AddressBook, (chain_address.address, blockchain_value))
            if existing:
                return existing.name
        
        # Then try multichain (NULL blockchain)
        existing = await self.session.get(AddressBook, (chain_address.address, ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE))
        if existing:
            return existing.name
        
        return None

    async def maybe_make_entry_name_multichain(
        self,
        address: ChecksumEvmAddress,
    ) -> None:
        """Make the existing name for the specified address apply to all chains.
        If there is no existing name or if there are different names for it in different chains,
        then no action is taken.
        """
        # Get all entries for this address
        statement = select(AddressBook).where(AddressBook.address == address)
        result = await self.session.execute(statement)
        entries = [row[0] for row in result]
        
        if not entries:
            return  # No entries found
        
        # Check if all have the same name
        names = {entry.name for entry in entries}
        if len(names) > 1:
            return  # Different names on different chains
        
        # All have the same name, make it multichain
        name = names.pop()
        
        # Delete all existing entries
        for entry in entries:
            self.session.delete(entry)
        
        # Add single multichain entry
        new_entry = AddressBook(
            address=address,
            name=name,
            blockchain=ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
        )
        self.session.add(new_entry)
        await self.session.commit()

    async def find_by(self, **kwargs) -> list[AddressBook]:
        """Find address book entries by criteria."""
        statement = select(AddressBook)
        
        for key, value in kwargs.items():
            if hasattr(AddressBook, key):
                statement = statement.where(getattr(AddressBook, key) == value)
        
        results = await self.session.execute(statement)
        return [row[0] for row in results.all()]