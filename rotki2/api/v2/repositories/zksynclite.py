"""Repository for zkSync Lite L2 transactions and swaps."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.zksynclite import (
    ZkSyncLiteSwap,
    ZkSyncLiteTransaction,
    ZkSyncLiteTxType,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ZkSyncLiteTransactionsRepository(AsyncBaseRepository[ZkSyncLiteTransaction]):
    """Repository for handling zkSync Lite transactions."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, ZkSyncLiteTransaction)

    async def get_transactions_by_address(
        self,
        address: str,
    ) -> list[ZkSyncLiteTransaction]:
        """Get all zkSync Lite transactions for an address.
        
        Args:
            address: The address to query
            
        Returns:
            List of zkSync Lite transactions
        """
        result = await self.session.exec(
            select(ZkSyncLiteTransaction).where(
                col(ZkSyncLiteTransaction.from_address) == address
            ).union(
                select(ZkSyncLiteTransaction).where(
                    col(ZkSyncLiteTransaction.to_address) == address
                )
            ).order_by(ZkSyncLiteTransaction.timestamp.desc())
        )
        return list(result.all())

    async def get_transactions_by_type(
        self,
        tx_type: str,
    ) -> list[ZkSyncLiteTransaction]:
        """Get all zkSync Lite transactions of a specific type.
        
        Args:
            tx_type: The transaction type
            
        Returns:
            List of zkSync Lite transactions
        """
        result = await self.session.exec(
            select(ZkSyncLiteTransaction).where(
                col(ZkSyncLiteTransaction.tx_type) == tx_type
            )
        )
        return list(result.all())

    async def get_transaction_by_hash(
        self,
        tx_hash: str,
    ) -> ZkSyncLiteTransaction | None:
        """Get a zkSync Lite transaction by its hash.
        
        Args:
            tx_hash: The transaction hash
            
        Returns:
            ZkSyncLiteTransaction if found, None otherwise
        """
        result = await self.session.exec(
            select(ZkSyncLiteTransaction).where(
                col(ZkSyncLiteTransaction.tx_hash) == tx_hash
            )
        )
        return result.first()


class ZkSyncLiteSwapsRepository(AsyncBaseRepository[ZkSyncLiteSwap]):
    """Repository for handling zkSync Lite swaps."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, ZkSyncLiteSwap)

    async def get_swaps_by_address(
        self,
        address: str,
    ) -> list[ZkSyncLiteSwap]:
        """Get all zkSync Lite swaps for an address.
        
        Args:
            address: The address to query
            
        Returns:
            List of zkSync Lite swaps
        """
        result = await self.session.exec(
            select(ZkSyncLiteSwap).where(
                col(ZkSyncLiteSwap.from_address) == address
            ).order_by(ZkSyncLiteSwap.timestamp.desc())
        )
        return list(result.all())

    async def get_swap_by_tx_hash(
        self,
        tx_hash: str,
    ) -> ZkSyncLiteSwap | None:
        """Get a zkSync Lite swap by transaction hash.
        
        Args:
            tx_hash: The transaction hash
            
        Returns:
            ZkSyncLiteSwap if found, None otherwise
        """
        result = await self.session.exec(
            select(ZkSyncLiteSwap).where(
                col(ZkSyncLiteSwap.tx_hash) == tx_hash
            )
        )
        return result.first()

    async def get_swaps_in_range(
        self,
        start_timestamp: int,
        end_timestamp: int,
        address: str | None = None,
    ) -> list[ZkSyncLiteSwap]:
        """Get zkSync Lite swaps within a timestamp range.
        
        Args:
            start_timestamp: Start of the time range
            end_timestamp: End of the time range
            address: Optional address filter
            
        Returns:
            List of zkSync Lite swaps
        """
        query = select(ZkSyncLiteSwap).where(
            col(ZkSyncLiteSwap.timestamp) >= start_timestamp,
            col(ZkSyncLiteSwap.timestamp) <= end_timestamp,
        )
        
        if address:
            query = query.where(col(ZkSyncLiteSwap.from_address) == address)
            
        query = query.order_by(ZkSyncLiteSwap.timestamp)
        
        result = await self.session.exec(query)
        return list(result.all())


class ZkSyncLiteTxTypeRepository(AsyncBaseRepository[ZkSyncLiteTxType]):
    """Repository for handling zkSync Lite transaction types."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, ZkSyncLiteTxType)

    async def get_all_tx_types(self) -> list[ZkSyncLiteTxType]:
        """Get all zkSync Lite transaction types.
        
        Returns:
            List of transaction types
        """
        result = await self.session.exec(select(ZkSyncLiteTxType))
        return list(result.all())