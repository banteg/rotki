"""Async AddressBook service for addressbook operations"""
from typing import TYPE_CHECKING, Any

from rotki2.api.v2.repositories.async_addressbook import AsyncAddressBookRepository
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookType,
    ChecksumEvmAddress,
    OptionalChainAddress,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


class AsyncAddressBookService:
    """Async service for addressbook operations"""

    def __init__(
        self,
        addressbook_repository: AsyncAddressBookRepository,
        book_type: AddressbookType,
        global_db: 'GlobalDBHandler | None' = None,
    ):
        self.addressbook_repository = addressbook_repository
        self.book_type = book_type
        self.global_db = global_db

    async def get_addressbook_entries(
        self,
        filter_query: AddressbookFilterQuery | None = None,
    ) -> dict[str, Any]:
        """Get addressbook entries with filtering"""
        entries, entries_found = await self.addressbook_repository.get_addressbook_entries(
            filter_query=filter_query,
        )
        
        # Get total count
        total_entries = await self.addressbook_repository.count()
        
        # Serialize entries
        serialized = [entry.serialize() for entry in entries]
        
        return {
            'entries': serialized,
            'entries_found': entries_found,
            'entries_total': total_entries,
        }

    async def add_addressbook_entries(
        self,
        entries: list[dict[str, Any]],
    ) -> dict[str, str]:
        """Add entries to addressbook"""
        addressbook_entries = []
        
        for entry_data in entries:
            # Parse blockchain if provided
            blockchain = None
            if entry_data.get('blockchain'):
                try:
                    blockchain = SupportedBlockchain(entry_data['blockchain'])
                except ValueError as e:
                    raise InputError(f'Invalid blockchain: {entry_data["blockchain"]}') from e
            
            # Validate address format for EVM chains
            address = entry_data['address']
            if blockchain and blockchain in (
                SupportedBlockchain.ETHEREUM,
                SupportedBlockchain.ETHEREUM_BEACONCHAIN,
            ):
                try:
                    from rotkehlchen.chain.evm.types import string_to_evm_address
                    address = string_to_evm_address(address)
                except ValueError as e:
                    raise InputError(f'Invalid EVM address: {address}') from e
            
            entry = AddressbookEntry(
                address=ChecksumEvmAddress(address),
                name=entry_data['name'],
                blockchain=blockchain,
            )
            addressbook_entries.append(entry)
        
        await self.addressbook_repository.add_or_update_addressbook_entries(addressbook_entries)
        
        return {'message': f'Added {len(addressbook_entries)} entries to addressbook'}

    async def update_addressbook_entries(
        self,
        entries: list[dict[str, Any]],
    ) -> dict[str, str]:
        """Update addressbook entries"""
        addressbook_entries = []
        
        for entry_data in entries:
            # Parse blockchain if provided
            blockchain = None
            if entry_data.get('blockchain'):
                try:
                    blockchain = SupportedBlockchain(entry_data['blockchain'])
                except ValueError as e:
                    raise InputError(f'Invalid blockchain: {entry_data["blockchain"]}') from e
            
            # Validate address format
            address = entry_data['address']
            if blockchain and blockchain in (
                SupportedBlockchain.ETHEREUM,
                SupportedBlockchain.ETHEREUM_BEACONCHAIN,
            ):
                try:
                    from rotkehlchen.chain.evm.types import string_to_evm_address
                    address = string_to_evm_address(address)
                except ValueError as e:
                    raise InputError(f'Invalid EVM address: {address}') from e
            
            entry = AddressbookEntry(
                address=ChecksumEvmAddress(address),
                name=entry_data['name'],
                blockchain=blockchain,
            )
            addressbook_entries.append(entry)
        
        try:
            await self.addressbook_repository.update_addressbook_entries(addressbook_entries)
        except InputError as e:
            raise InputError(str(e)) from e
        
        return {'message': f'Updated {len(addressbook_entries)} entries in addressbook'}

    async def delete_addressbook_entries(
        self,
        chain_addresses: list[OptionalChainAddress],
    ) -> dict[str, str]:
        """Delete addressbook entries"""
        try:
            await self.addressbook_repository.delete_addressbook_entries(chain_addresses)
        except InputError as e:
            raise InputError(str(e)) from e
        
        return {'message': f'Deleted {len(chain_addresses)} entries from addressbook'}

    async def get_addressbook_entry_name(
        self,
        chain_address: OptionalChainAddress,
    ) -> str | None:
        """Get the name for a specific address and blockchain"""
        return await self.addressbook_repository.get_addressbook_entry_name(chain_address)

    async def maybe_make_entry_name_multichain(
        self,
        address: ChecksumEvmAddress,
    ) -> None:
        """Make an address's name apply to all chains if possible"""
        await self.addressbook_repository.maybe_make_entry_name_multichain(address)