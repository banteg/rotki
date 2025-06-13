"""Repository for Cowswap DEX orders."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.defi import CowswapOrder

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CowswapOrdersRepository(AsyncBaseRepository[CowswapOrder]):
    """Repository for handling Cowswap orders."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, CowswapOrder)

    async def get_by_order_id(self, order_id: str) -> CowswapOrder | None:
        """Get a Cowswap order by its order ID.
        
        Args:
            order_id: The order ID
            
        Returns:
            CowswapOrder if found, None otherwise
        """
        result = await self.session.exec(
            select(CowswapOrder).where(
                col(CowswapOrder.order_id) == order_id
            )
        )
        return result.first()

    async def get_by_account(self, account: str) -> list[CowswapOrder]:
        """Get all Cowswap orders for a specific account.
        
        Args:
            account: The account address
            
        Returns:
            List of Cowswap orders
        """
        result = await self.session.exec(
            select(CowswapOrder).where(
                col(CowswapOrder.account) == account
            ).order_by(CowswapOrder.timestamp.desc())
        )
        return list(result.all())

    async def get_orders_in_range(
        self,
        start_timestamp: int,
        end_timestamp: int,
        account: str | None = None,
    ) -> list[CowswapOrder]:
        """Get Cowswap orders within a timestamp range.
        
        Args:
            start_timestamp: Start of the time range
            end_timestamp: End of the time range
            account: Optional account filter
            
        Returns:
            List of Cowswap orders
        """
        query = select(CowswapOrder).where(
            col(CowswapOrder.timestamp) >= start_timestamp,
            col(CowswapOrder.timestamp) <= end_timestamp,
        )
        
        if account:
            query = query.where(col(CowswapOrder.account) == account)
            
        query = query.order_by(CowswapOrder.timestamp)
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_pending_orders(self) -> list[CowswapOrder]:
        """Get all pending Cowswap orders.
        
        Returns:
            List of pending orders
        """
        result = await self.session.exec(
            select(CowswapOrder).where(
                col(CowswapOrder.status) == 'pending'
            ).order_by(CowswapOrder.timestamp)
        )
        return list(result.all())

    async def update_order_status(
        self,
        order_id: str,
        status: str,
        tx_hash: str | None = None,
    ) -> CowswapOrder | None:
        """Update the status of a Cowswap order.
        
        Args:
            order_id: The order ID
            status: The new status
            tx_hash: Optional transaction hash (for executed orders)
            
        Returns:
            Updated CowswapOrder if found, None otherwise
        """
        order = await self.get_by_order_id(order_id)
        
        if order:
            order.status = status
            if tx_hash:
                order.tx_hash = tx_hash
            self.session.add(order)
            await self.session.commit()
            return order
            
        return None