"""Async Loopring repository for v2 API.

Handles all Loopring-related async database operations.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from rotkehlchen.api.v2.repositories.async_base import AsyncBaseRepository
from rotkehlchen.db.models.user.cache import MultiSettings
from rotkehlchen.types import ChecksumEvmAddress


class AsyncLoopringRepository(AsyncBaseRepository[MultiSettings]):
    """Async repository for Loopring account mappings."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, MultiSettings)
    
    async def add_accountid_mapping(
        self,
        address: ChecksumEvmAddress,
        account_id: int,
    ) -> None:
        """Add a Loopring account ID mapping for an address."""
        name = f'loopring_{address}_account_id'
        value = str(account_id)
        
        # Check if mapping exists
        existing = await self.session.get(MultiSettings, (name, value))
        
        if not existing:
            # Create new mapping
            mapping = MultiSettings(name=name, value=value)
            self.session.add(mapping)
            await self.session.commit()
    
    async def remove_accountid_mapping(self, address: ChecksumEvmAddress) -> None:
        """Remove the Loopring account ID mapping for an address."""
        name = f'loopring_{address}_account_id'
        
        # Find and delete all entries with this name
        statement = select(MultiSettings).where(MultiSettings.name == name)
        result = await self.session.execute(statement)
        
        for row in result:
            self.session.delete(row[0])
        
        await self.session.commit()
    
    async def get_accountid_mapping(self, address: ChecksumEvmAddress) -> int | None:
        """Get the Loopring account ID for an address.
        
        Returns None if no mapping exists.
        """
        name = f'loopring_{address}_account_id'
        
        statement = select(MultiSettings).where(MultiSettings.name == name)
        result = await self.session.execute(statement)
        first_result = result.first()
        
        if first_result is None:
            return None
        
        return int(first_result[0].value)
    
    async def find_by(self, **kwargs) -> list[MultiSettings]:
        """Find Loopring mappings by criteria."""
        statement = select(MultiSettings)
        
        # Filter for Loopring entries
        statement = statement.where(MultiSettings.name.like('loopring_%'))
        
        for key, value in kwargs.items():
            if hasattr(MultiSettings, key):
                statement = statement.where(getattr(MultiSettings, key) == value)
        
        results = await self.session.execute(statement)
        return [row[0] for row in results.all()]