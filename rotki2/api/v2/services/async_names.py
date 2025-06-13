"""Async Names service for ENS and addressbook operations"""
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.addressbook import AddressBookRepository
from rotki2.api.v2.repositories.ens import ENSRepository
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookType,
    ChecksumEvmAddress,
    EnsMapping,
    OptionalChainAddress,
    SupportedBlockchain,
    Timestamp,
)

if TYPE_CHECKING:
    from rotki2.utils.async_http_client import AsyncHTTPClient


class AsyncNamesService:
    """Async service for names and addressbook operations"""

    def __init__(
        self,
        session: AsyncSession,
        http_client: 'AsyncHTTPClient | None' = None,
    ):
        self.session = session
        self.addressbook_repo = AddressBookRepository(session)
        self.ens_repo = ENSRepository(session)
        self.http_client = http_client

    async def reverse_ens_lookup(
        self,
        ethereum_addresses: list[ChecksumEvmAddress],
        ignore_cache: bool = False,
    ) -> dict[ChecksumEvmAddress, str | None]:
        """Perform reverse ENS lookup for Ethereum addresses
        
        Returns a mapping of address -> ENS name (or None if not found)
        """
        # First check cache if not ignoring it
        if not ignore_cache:
            cached_mappings = await self.ens_repo.get_reverse_ens(ethereum_addresses)
            
            # Separate cached results and addresses to query
            result = {}
            addresses_to_query = []
            
            for address in ethereum_addresses:
                if address in cached_mappings:
                    mapping = cached_mappings[address]
                    if isinstance(mapping, EnsMapping):
                        result[address] = mapping.name
                    else:  # It's a Timestamp, meaning we checked and found no name
                        result[address] = None
                else:
                    addresses_to_query.append(address)
        else:
            addresses_to_query = ethereum_addresses
            result = {}
        
        # Query remaining addresses
        if addresses_to_query and self.http_client:
            # In production, this would call ENS contracts
            # For now, simulate with empty results
            ens_lookup_results = {}
            for address in addresses_to_query:
                ens_lookup_results[address] = None  # Simulated empty result
            
            # Update cache
            mappings_to_send = {}
            await self.ens_repo.update_values(ens_lookup_results, mappings_to_send)
            
            # Add to results
            result.update(ens_lookup_results)
        
        return result

    async def resolve_ens_names(
        self,
        name: str,
        ignore_cache: bool = False,
    ) -> ChecksumEvmAddress | None:
        """Resolve ENS name to Ethereum address"""
        # First check cache if not ignoring it
        if not ignore_cache:
            cached_address = await self.ens_repo.get_address_for_name(name)
            if cached_address:
                return cached_address
        
        # Query ENS if we have HTTP client
        if self.http_client:
            # In production, this would call ENS contracts
            # For now, return None to simulate not found
            return None
        
        return None

    async def get_ens_avatar(
        self,
        ens_name: str,
        ignore_cache: bool = False,
    ) -> str | None:
        """Get ENS avatar URL for a given ENS name"""
        if not ignore_cache:
            # Check if we have a recent avatar check
            try:
                last_update = await self.ens_repo.get_last_avatar_update(ens_name)
                # If checked recently (within 7 days), skip
                from rotkehlchen.utils.misc import ts_now
                if ts_now() - last_update < 604800:  # 7 days
                    return None
            except InputError:
                # ENS name not tracked yet
                pass
        
        # In production, this would query ENS contracts for avatar
        # For now, return None
        return None

    async def get_addressbook_entries(
        self,
        book_type: AddressbookType,
        filter_query: AddressbookFilterQuery | None = None,
    ) -> tuple[list[AddressbookEntry], int]:
        """Get addressbook entries with filtering
        
        Returns (entries, total_count)
        """
        # For global addressbook (book_type == GLOBAL), we'd use a different table
        # For now, we'll use the user addressbook for all types
        return await self.addressbook_repo.get_addressbook_entries(filter_query)

    async def add_addressbook_entries(
        self,
        book_type: AddressbookType,
        entries: list[AddressbookEntry],
    ) -> None:
        """Add entries to addressbook"""
        # Validate entries
        for entry in entries:
            if entry.blockchain and entry.blockchain.is_evm():
                # Validate EVM address format
                try:
                    from rotkehlchen.chain.evm.types import string_to_evm_address
                    string_to_evm_address(entry.address)
                except ValueError as e:
                    raise InputError(f'Invalid EVM address: {entry.address}') from e
        
        # Add to repository
        await self.addressbook_repo.add_or_update_addressbook_entries(entries)

    async def update_addressbook_entries(
        self,
        book_type: AddressbookType,
        entries: list[AddressbookEntry],
    ) -> None:
        """Update addressbook entries"""
        # Validate entries
        for entry in entries:
            if entry.blockchain and entry.blockchain.is_evm():
                # Validate EVM address format
                try:
                    from rotkehlchen.chain.evm.types import string_to_evm_address
                    string_to_evm_address(entry.address)
                except ValueError as e:
                    raise InputError(f'Invalid EVM address: {entry.address}') from e
        
        # Update in repository
        await self.addressbook_repo.update_addressbook_entries(entries)

    async def delete_addressbook_entries(
        self,
        book_type: AddressbookType,
        chain_addresses: list[OptionalChainAddress],
    ) -> None:
        """Delete addressbook entries"""
        await self.addressbook_repo.delete_addressbook_entries(chain_addresses)

    async def search_names_everywhere(
        self,
        addresses: list[OptionalChainAddress],
    ) -> list[dict[str, str | None]]:
        """Search for names in all available sources (ENS, addressbook, etc.)
        
        Returns list of mappings with address, name, and blockchain
        """
        results = []
        
        # First check addressbook
        for chain_address in addresses:
            address, blockchain = chain_address
            
            # Check addressbook first
            name = await self.addressbook_repo.get_addressbook_entry_name(
                chain_address=chain_address
            )
            
            if name:
                results.append({
                    'address': address,
                    'name': name,
                    'blockchain': blockchain.value if blockchain else None,
                })
            elif blockchain is None or blockchain == SupportedBlockchain.ETHEREUM:
                # If no addressbook entry and it's Ethereum, check ENS
                ens_mapping = await self.reverse_ens_lookup(
                    [ChecksumEvmAddress(address)],
                    ignore_cache=False,
                )
                ens_name = ens_mapping.get(ChecksumEvmAddress(address))
                results.append({
                    'address': address,
                    'name': ens_name,
                    'blockchain': SupportedBlockchain.ETHEREUM.value,
                })
            else:
                # No name found
                results.append({
                    'address': address,
                    'name': None,
                    'blockchain': blockchain.value if blockchain else None,
                })
        
        return results

    async def make_entry_multichain(
        self,
        address: ChecksumEvmAddress,
    ) -> None:
        """Make an addressbook entry apply to all chains"""
        await self.addressbook_repo.maybe_make_entry_name_multichain(address)