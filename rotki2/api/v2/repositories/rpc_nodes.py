"""Repository for RPC nodes configuration."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.nodes import RPCNode

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RPCNodesRepository(AsyncBaseRepository[RPCNode]):
    """Repository for handling RPC nodes configuration."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, RPCNode)

    async def get_by_blockchain(self, blockchain: str) -> list[RPCNode]:
        """Get all RPC nodes for a specific blockchain.
        
        Args:
            blockchain: The blockchain identifier
            
        Returns:
            List of RPC nodes
        """
        result = await self.session.exec(
            select(RPCNode).where(
                col(RPCNode.blockchain) == blockchain
            )
        )
        return list(result.all())

    async def get_active_nodes(self) -> list[RPCNode]:
        """Get all active RPC nodes.
        
        Returns:
            List of active RPC nodes
        """
        result = await self.session.exec(
            select(RPCNode).where(
                col(RPCNode.active) == True  # noqa: E712
            )
        )
        return list(result.all())

    async def get_node_by_endpoint(self, endpoint: str) -> RPCNode | None:
        """Get an RPC node by its endpoint URL.
        
        Args:
            endpoint: The RPC endpoint URL
            
        Returns:
            RPCNode if found, None otherwise
        """
        result = await self.session.exec(
            select(RPCNode).where(
                col(RPCNode.endpoint) == endpoint
            )
        )
        return result.first()
