"""Repository for unresolved remote conflicts."""
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.conflicts import UnresolvedRemoteConflict

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ConflictsRepository(AsyncBaseRepository[UnresolvedRemoteConflict]):
    """Repository for handling unresolved remote conflicts."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, UnresolvedRemoteConflict)

    async def get_all_conflicts(self) -> list[UnresolvedRemoteConflict]:
        """Get all unresolved conflicts.
        
        Returns:
            List of all unresolved conflicts
        """
        result = await self.session.exec(
            select(UnresolvedRemoteConflict).order_by(
                UnresolvedRemoteConflict.created_at.desc()
            )
        )
        return list(result.all())

    async def get_conflicts_by_type(
        self,
        conflict_type: str,
    ) -> list[UnresolvedRemoteConflict]:
        """Get conflicts of a specific type.
        
        Args:
            conflict_type: The type of conflict
            
        Returns:
            List of conflicts of the specified type
        """
        result = await self.session.exec(
            select(UnresolvedRemoteConflict).where(
                col(UnresolvedRemoteConflict.conflict_type) == conflict_type
            ).order_by(UnresolvedRemoteConflict.created_at.desc())
        )
        return list(result.all())

    async def add_conflict(
        self,
        conflict_type: str,
        local_data: Any,
        remote_data: Any,
        details: dict | None = None,
    ) -> UnresolvedRemoteConflict:
        """Add a new unresolved conflict.
        
        Args:
            conflict_type: The type of conflict
            local_data: The local version of the data
            remote_data: The remote version of the data
            details: Optional additional details
            
        Returns:
            Created UnresolvedRemoteConflict instance
        """
        conflict = UnresolvedRemoteConflict(
            conflict_type=conflict_type,
            local_data=local_data,
            remote_data=remote_data,
            details=details or {},
        )
        return await self.create(conflict)

    async def resolve_conflict(
        self,
        conflict_id: int,
        resolution: str,
        resolved_data: Any,
    ) -> bool:
        """Resolve a conflict.
        
        Args:
            conflict_id: The conflict ID
            resolution: How the conflict was resolved ('local', 'remote', 'merge')
            resolved_data: The final resolved data
            
        Returns:
            True if resolved, False if not found
        """
        conflict = await self.get_by_id(conflict_id)
        
        if conflict:
            # Store resolution info and remove the conflict
            conflict.resolution = resolution
            conflict.resolved_data = resolved_data
            await self.delete(conflict)
            return True
            
        return False

    async def get_conflicts_count(self) -> int:
        """Get the total number of unresolved conflicts.
        
        Returns:
            Number of unresolved conflicts
        """
        result = await self.session.exec(
            select(UnresolvedRemoteConflict)
        )
        return len(result.all())