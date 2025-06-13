"""Async Loopring service for Loopring operations"""
from typing import TYPE_CHECKING

from rotki2.api.v2.repositories.loopring import LoopringRepository
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.exchanges.loopring import Loopring


class AsyncLoopringService:
    """Async service for Loopring operations"""
    
    def __init__(
        self,
        loopring_repository: LoopringRepository,
        loopring_exchange: 'Loopring | None' = None,
    ):
        self.loopring_repository = loopring_repository
        self.loopring_exchange = loopring_exchange
    
    async def add_account_mapping(
        self,
        address: ChecksumEvmAddress,
        account_id: int,
    ) -> dict[str, str]:
        """Add a Loopring account ID mapping."""
        await self.loopring_repository.add_accountid_mapping(address, account_id)
        return {'message': f'Added Loopring account mapping for {address}'}
    
    async def remove_account_mapping(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, str]:
        """Remove a Loopring account ID mapping."""
        await self.loopring_repository.remove_accountid_mapping(address)
        return {'message': f'Removed Loopring account mapping for {address}'}
    
    async def get_account_mapping(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, int | None]:
        """Get the Loopring account ID for an address."""
        account_id = await self.loopring_repository.get_accountid_mapping(address)
        return {'account_id': account_id}
    
    async def get_all_mappings(self) -> dict[str, list[dict[str, str | int]]]:
        """Get all Loopring account mappings."""
        mappings = await self.loopring_repository.find_by()
        
        result = []
        for mapping in mappings:
            # Extract address from name (format: loopring_{address}_account_id)
            parts = mapping.name.split('_')
            if len(parts) >= 3 and parts[0] == 'loopring' and parts[-2] == 'account' and parts[-1] == 'id':
                address = '_'.join(parts[1:-2])
                result.append({
                    'address': address,
                    'account_id': int(mapping.value),
                })
        
        return {'mappings': result}
    
    async def sync_account_data(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, str]:
        """Sync account data from Loopring API if exchange is available."""
        if self.loopring_exchange is None:
            return {'message': 'Loopring exchange not configured'}
        
        # This would typically call the Loopring exchange API
        # to fetch and update account data
        # For now, we just return a placeholder message
        return {'message': f'Account data sync initiated for {address}'}