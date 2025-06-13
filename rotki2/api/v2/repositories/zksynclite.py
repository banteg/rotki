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

    async def get_undecoded_transactions(self) -> list[ZkSyncLiteTransaction]:
        """Get all undecoded zkSync Lite transactions.
        
        Returns:
            List of undecoded transactions
        """
        result = await self.session.exec(
            select(ZkSyncLiteTransaction).where(
                col(ZkSyncLiteTransaction.is_decoded) == 0
            ).order_by(ZkSyncLiteTransaction.timestamp)
        )
        return list(result.all())

    async def mark_as_decoded(
        self,
        tx_identifier: int,
    ) -> ZkSyncLiteTransaction | None:
        """Mark a transaction as decoded.
        
        Args:
            tx_identifier: The transaction identifier
            
        Returns:
            Updated transaction if found, None otherwise
        """
        tx = await self.get(tx_identifier)
        if tx:
            tx.is_decoded = 1
            self.session.add(tx)
            await self.session.commit()
            return tx
        return None

    async def get_transactions_in_range(
        self,
        start_timestamp: int,
        end_timestamp: int,
        address: str | None = None,
        tx_type: str | None = None,
    ) -> list[ZkSyncLiteTransaction]:
        """Get zkSync Lite transactions within a timestamp range.
        
        Args:
            start_timestamp: Start of the time range
            end_timestamp: End of the time range
            address: Optional address filter
            tx_type: Optional transaction type filter
            
        Returns:
            List of zkSync Lite transactions
        """
        query = select(ZkSyncLiteTransaction).where(
            col(ZkSyncLiteTransaction.timestamp) >= start_timestamp,
            col(ZkSyncLiteTransaction.timestamp) <= end_timestamp,
        )
        
        if address:
            query = query.where(
                (col(ZkSyncLiteTransaction.from_address) == address) |
                (col(ZkSyncLiteTransaction.to_address) == address)
            )
        
        if tx_type:
            query = query.where(col(ZkSyncLiteTransaction.type) == tx_type)
            
        query = query.order_by(ZkSyncLiteTransaction.timestamp)
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_transaction_volume_by_asset(
        self,
        address: str | None = None,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[dict[str, str]]:
        """Get transaction volume grouped by asset.
        
        Args:
            address: Optional address filter
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of dicts with asset, transaction_count, and total_amount
        """
        from sqlalchemy import func
        
        query = select(
            ZkSyncLiteTransaction.asset,
            func.count(ZkSyncLiteTransaction.identifier).label('transaction_count'),
            func.sum(ZkSyncLiteTransaction.amount).label('total_amount'),
        ).group_by(ZkSyncLiteTransaction.asset)
        
        if address:
            query = query.where(
                (col(ZkSyncLiteTransaction.from_address) == address) |
                (col(ZkSyncLiteTransaction.to_address) == address)
            )
        
        if start_timestamp:
            query = query.where(col(ZkSyncLiteTransaction.timestamp) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(ZkSyncLiteTransaction.timestamp) <= end_timestamp)
        
        result = await self.session.exec(query)
        
        return [
            {
                'asset': row[0],
                'transaction_count': str(row[1]),
                'total_amount': str(row[2] or 0),
            }
            for row in result.all()
        ]


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
        # Join with transactions to get timestamps
        from sqlalchemy.orm import selectinload
        
        query = select(ZkSyncLiteSwap).join(
            ZkSyncLiteTransaction,
            ZkSyncLiteSwap.tx_id == ZkSyncLiteTransaction.identifier
        ).where(
            col(ZkSyncLiteTransaction.timestamp) >= start_timestamp,
            col(ZkSyncLiteTransaction.timestamp) <= end_timestamp,
        ).options(selectinload(ZkSyncLiteSwap.transaction))
        
        if address:
            query = query.where(col(ZkSyncLiteTransaction.from_address) == address)
            
        query = query.order_by(ZkSyncLiteTransaction.timestamp)
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_swap_by_tx_id(self, tx_id: int) -> ZkSyncLiteSwap | None:
        """Get a zkSync Lite swap by transaction ID.
        
        Args:
            tx_id: The transaction identifier
            
        Returns:
            ZkSyncLiteSwap if found, None otherwise
        """
        result = await self.session.exec(
            select(ZkSyncLiteSwap).where(
                col(ZkSyncLiteSwap.tx_id) == tx_id
            )
        )
        return result.first()

    async def get_swaps_by_asset(
        self,
        asset: str,
        is_from_asset: bool = True,
    ) -> list[ZkSyncLiteSwap]:
        """Get all swaps involving a specific asset.
        
        Args:
            asset: The asset identifier
            is_from_asset: If True, search in from_asset, else in to_asset
            
        Returns:
            List of zkSync Lite swaps
        """
        if is_from_asset:
            query = select(ZkSyncLiteSwap).where(
                col(ZkSyncLiteSwap.from_asset) == asset
            )
        else:
            query = select(ZkSyncLiteSwap).where(
                col(ZkSyncLiteSwap.to_asset) == asset
            )
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_swap_volume_by_pair(
        self,
        address: str | None = None,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[dict[str, str]]:
        """Get swap volume grouped by asset pair.
        
        Args:
            address: Optional address filter
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of dicts with from_asset, to_asset, swap_count, and total_from_amount
        """
        from sqlalchemy import func
        
        query = select(
            ZkSyncLiteSwap.from_asset,
            ZkSyncLiteSwap.to_asset,
            func.count(ZkSyncLiteSwap.tx_id).label('swap_count'),
            func.sum(ZkSyncLiteSwap.from_amount).label('total_from_amount'),
        ).join(
            ZkSyncLiteTransaction,
            ZkSyncLiteSwap.tx_id == ZkSyncLiteTransaction.identifier
        ).group_by(
            ZkSyncLiteSwap.from_asset,
            ZkSyncLiteSwap.to_asset
        )
        
        if address:
            query = query.where(col(ZkSyncLiteTransaction.from_address) == address)
        
        if start_timestamp:
            query = query.where(col(ZkSyncLiteTransaction.timestamp) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(ZkSyncLiteTransaction.timestamp) <= end_timestamp)
        
        result = await self.session.exec(query)
        
        return [
            {
                'from_asset': row[0],
                'to_asset': row[1],
                'swap_count': str(row[2]),
                'total_from_amount': str(row[3] or 0),
            }
            for row in result.all()
        ]


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