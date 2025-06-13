"""Names service for ENS and addressbook operations"""
from typing import TYPE_CHECKING, Any

# ResolverName type - simple string alias for ENS names
ResolverName = str
from rotkehlchen.chain.evm.names import search_for_addresses_names
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookType,
    ChecksumEvmAddress,
    OptionalChainAddress,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.addressbook.addressbook import AddressbookPrioritizer
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.data_handler import DataHandler
    from rotkehlchen.db.repository.addressbook import AddressbookRepository


class NamesService:
    """Service for names and addressbook operations"""

    def __init__(
        self,
        db_connection: DBConnection,
        chains_aggregator: 'ChainsAggregator | None' = None,
        data_handler: 'DataHandler | None' = None,
        addressbook_prioritizer: 'AddressbookPrioritizer | None' = None,
    ):
        self.db_connection = db_connection
        self.chains_aggregator = chains_aggregator
        self.data = data_handler
        self.addressbook_prioritizer = addressbook_prioritizer

    @property
    def addressbook_repo(self) -> 'AddressbookRepository':
        """Get addressbook repository"""
        if self.data is None:
            raise ValueError('Data handler not initialized')
        return self.data.db.repos.address_book

    def reverse_ens_lookup(
        self,
        ethereum_addresses: list[ChecksumEvmAddress],
        ignore_cache: bool = False,
    ) -> dict[str, str | None]:
        """Perform reverse ENS lookup for Ethereum addresses"""
        if self.chains_aggregator is None:
            raise ValueError('Chains aggregator not initialized')

        eth_manager = self.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)
        if eth_manager is None:
            raise ValueError('Ethereum manager not found')

        ens_mappings = {}
        for address in ethereum_addresses:
            try:
                domain = eth_manager.ens_lookup(
                    address=address,
                    name_type=ResolverName.DOMAIN,
                    ignore_cache=ignore_cache,
                )
                ens_mappings[address] = domain
            except (RemoteError, InputError):
                ens_mappings[address] = None

        return ens_mappings

    def resolve_ens_names(
        self,
        name: str,
        ignore_cache: bool = False,
    ) -> ChecksumEvmAddress | None:
        """Resolve ENS name to Ethereum address"""
        if self.chains_aggregator is None:
            raise ValueError('Chains aggregator not initialized')

        eth_manager = self.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)
        if eth_manager is None:
            raise ValueError('Ethereum manager not found')

        try:
            address = eth_manager.resolve_ens_name(
                name=name,
                ignore_cache=ignore_cache,
            )
            return address
        except (RemoteError, InputError):
            return None

    def get_ens_avatar(self, ens_name: str) -> str | None:
        """Get ENS avatar URL for a given ENS name"""
        if self.chains_aggregator is None:
            raise ValueError('Chains aggregator not initialized')

        eth_manager = self.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)
        if eth_manager is None:
            raise ValueError('Ethereum manager not found')

        try:
            # First resolve the ENS name to get the address
            address = eth_manager.resolve_ens_name(name=ens_name)
            if address is None:
                return None

            # Then look up the avatar
            avatar = eth_manager.ens_lookup(
                address=address,
                name_type=ResolverName.AVATAR,
                ignore_cache=False,
            )
            return avatar
        except (RemoteError, InputError):
            return None

    def search_names_everywhere(
        self,
        addresses: list[OptionalChainAddress],
    ) -> list[dict[str, Any]]:
        """Search for names in all available sources (ENS, addressbook, etc.)"""
        if self.addressbook_prioritizer is None:
            raise ValueError('Addressbook prioritizer not initialized')

        mappings = search_for_addresses_names(
            prioritizer=self.addressbook_prioritizer,
            chain_addresses=addresses,
        )

        # Serialize the results
        serialized = []
        for mapping in mappings:
            serialized.append({
                'address': mapping.address,
                'name': mapping.name,
                'blockchain': mapping.blockchain.value if mapping.blockchain else None,
            })

        return serialized

    def get_addressbook_entries(
        self,
        book_type: AddressbookType,
        filter_query: AddressbookFilterQuery,
    ) -> dict[str, Any]:
        """Get addressbook entries with filtering"""
        entries, entries_found = self.addressbook_repo.get_entries(
            book_type=book_type,
            filter_query=filter_query,
        )
        entries_total = self.addressbook_repo.get_entries_count(book_type=book_type)

        serialized = [entry.serialize() for entry in entries]

        return {
            'entries': serialized,
            'entries_found': entries_found,
            'entries_total': entries_total,
        }

    def add_addressbook_entries(
        self,
        book_type: AddressbookType,
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

            # Validate address format
            address = entry_data['address']
            if blockchain and blockchain in (SupportedBlockchain.ETHEREUM, SupportedBlockchain.ETHEREUM_BEACONCHAIN):
                try:
                    address = string_to_evm_address(address)
                except ValueError as e:
                    raise InputError(f'Invalid EVM address: {address}') from e

            entry = AddressbookEntry(
                address=address,
                name=entry_data['name'],
                blockchain=blockchain,
            )
            addressbook_entries.append(entry)

        with self.data.db.repos.unit_of_work():
            self.addressbook_repo.add_or_update_entries(
                book_type=book_type,
                entries=addressbook_entries,
            )

        return {'message': f'Added {len(addressbook_entries)} entries to addressbook'}

    def update_addressbook_entries(
        self,
        book_type: AddressbookType,
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
            if blockchain and blockchain in (SupportedBlockchain.ETHEREUM, SupportedBlockchain.ETHEREUM_BEACONCHAIN):
                try:
                    address = string_to_evm_address(address)
                except ValueError as e:
                    raise InputError(f'Invalid EVM address: {address}') from e

            entry = AddressbookEntry(
                address=address,
                name=entry_data['name'],
                blockchain=blockchain,
            )
            addressbook_entries.append(entry)

        try:
            with self.data.db.repos.unit_of_work():
                self.addressbook_repo.update_entries(
                    book_type=book_type,
                    entries=addressbook_entries,
                )
        except InputError as e:
            raise InputError(str(e)) from e

        return {'message': f'Updated {len(addressbook_entries)} entries in addressbook'}

    def delete_addressbook_entries(
        self,
        book_type: AddressbookType,
        chain_addresses: list[OptionalChainAddress],
    ) -> dict[str, str]:
        """Delete addressbook entries"""
        try:
            with self.data.db.repos.unit_of_work():
                self.addressbook_repo.delete_entries(
                    book_type=book_type,
                    chain_addresses=chain_addresses,
                )
        except InputError as e:
            raise InputError(str(e)) from e

        return {'message': f'Deleted {len(chain_addresses)} entries from addressbook'}
