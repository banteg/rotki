"""Async ENS service for ENS operations"""
from typing import TYPE_CHECKING

from rotki2.api.v2.repositories.ens import ENSRepository
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator


class AsyncENSService:
    """Async service for ENS operations"""

    def __init__(
        self,
        ens_repository: ENSRepository,
        chains_aggregator: 'ChainsAggregator | None' = None,
    ):
        self.ens_repository = ens_repository
        self.chains_aggregator = chains_aggregator

    async def reverse_ens_lookup(
        self,
        ethereum_addresses: list[ChecksumEvmAddress],
        ignore_cache: bool = False,
    ) -> dict[ChecksumEvmAddress, str | None]:
        """Perform reverse ENS lookup for Ethereum addresses"""
        if not ignore_cache:
            # First check cache
            cached_data = await self.ens_repository.get_reverse_ens(ethereum_addresses)

            # Separate addresses that need fresh lookup
            addresses_to_lookup = []
            result = {}
            now = ts_now()

            for address in ethereum_addresses:
                if address in cached_data:
                    cached_item = cached_data[address]
                    # If it's a Timestamp, it means no ENS name found previously
                    if isinstance(cached_item, Timestamp):
                        # Check if cache is still valid (e.g., less than 24 hours old)
                        if now - cached_item < 86400:  # 24 hours
                            result[address] = None
                            continue
                    else:
                        # It's an EnsMapping
                        result[address] = cached_item.name
                        continue
                addresses_to_lookup.append(address)
        else:
            addresses_to_lookup = ethereum_addresses
            result = {}

        # Lookup remaining addresses if chains aggregator is available
        if addresses_to_lookup and self.chains_aggregator is not None:
            from rotkehlchen.types import SupportedBlockchain

            eth_manager = self.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)
            if eth_manager is not None:
                ens_lookup_results = {}

                for address in addresses_to_lookup:
                    try:
                        # This would need to be made async in the actual implementation
                        # For now, we're just preparing the structure
                        domain = eth_manager.ens_lookup(
                            address=address,
                            name_type='domain',
                            ignore_cache=True,
                        )
                        ens_lookup_results[address] = domain
                        result[address] = domain
                    except Exception:
                        ens_lookup_results[address] = None
                        result[address] = None

                # Update cache with new results
                await self.ens_repository.update_values(ens_lookup_results, {})

        return result

    async def resolve_ens_name(
        self,
        name: str,
        ignore_cache: bool = False,
    ) -> ChecksumEvmAddress | None:
        """Resolve ENS name to Ethereum address"""
        if not ignore_cache:
            # Check cache first
            cached_address = await self.ens_repository.get_address_for_name(name)
            if cached_address is not None:
                return cached_address

        # If not in cache or ignoring cache, lookup via chain
        if self.chains_aggregator is not None:
            from rotkehlchen.types import SupportedBlockchain

            eth_manager = self.chains_aggregator.get_chain_manager(SupportedBlockchain.ETHEREUM)
            if eth_manager is not None:
                try:
                    # This would need to be made async in the actual implementation
                    address = eth_manager.resolve_ens_name(
                        name=name,
                        ignore_cache=True,
                    )

                    # Cache the result
                    if address is not None:
                        await self.ens_repository.add_ens_mapping(
                            address=address,
                            name=name,
                        )

                    return address
                except Exception:
                    return None

        return None

    async def get_ens_avatar_update_time(self, ens_name: str) -> Timestamp:
        """Get the last time an ENS avatar was updated"""
        return await self.ens_repository.get_last_avatar_update(ens_name)
