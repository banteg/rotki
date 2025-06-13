"""Repository for exchange margin positions."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.trading import MarginPosition

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class MarginPositionsRepository(AsyncBaseRepository[MarginPosition]):
    """Repository for handling margin positions."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, MarginPosition)

    async def get_by_exchange(self, exchange: str) -> list[MarginPosition]:
        """Get all margin positions for a specific exchange.
        
        Args:
            exchange: The exchange name
            
        Returns:
            List of margin positions
        """
        result = await self.session.exec(
            select(MarginPosition).where(
                col(MarginPosition.exchange) == exchange
            ).order_by(MarginPosition.open_time.desc())
        )
        return list(result.all())

    async def get_open_positions(self) -> list[MarginPosition]:
        """Get all open margin positions.
        
        Returns:
            List of open margin positions
        """
        result = await self.session.exec(
            select(MarginPosition).where(
                col(MarginPosition.close_time).is_(None)
            ).order_by(MarginPosition.open_time.desc())
        )
        return list(result.all())

    async def get_closed_positions(
        self,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[MarginPosition]:
        """Get closed margin positions within a time range.
        
        Args:
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of closed margin positions
        """
        query = select(MarginPosition).where(
            col(MarginPosition.close_time).is_not(None)
        )
        
        if start_timestamp is not None:
            query = query.where(col(MarginPosition.close_time) >= start_timestamp)
        if end_timestamp is not None:
            query = query.where(col(MarginPosition.close_time) <= end_timestamp)
            
        query = query.order_by(MarginPosition.close_time.desc())
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_position_by_id(
        self,
        position_id: str,
        exchange: str,
    ) -> MarginPosition | None:
        """Get a specific margin position by ID and exchange.
        
        Args:
            position_id: The position ID
            exchange: The exchange name
            
        Returns:
            MarginPosition if found, None otherwise
        """
        result = await self.session.exec(
            select(MarginPosition).where(
                col(MarginPosition.position_id) == position_id,
                col(MarginPosition.exchange) == exchange,
            )
        )
        return result.first()

    async def close_position(
        self,
        position_id: str,
        exchange: str,
        close_time: int,
        close_price: str,
        profit_loss: str,
    ) -> MarginPosition | None:
        """Close a margin position.
        
        Args:
            position_id: The position ID
            exchange: The exchange name
            close_time: The closing timestamp
            close_price: The closing price
            profit_loss: The realized profit/loss
            
        Returns:
            Updated MarginPosition if found, None otherwise
        """
        position = await self.get_position_by_id(position_id, exchange)
        
        if position and position.close_time is None:
            position.close_time = close_time
            position.close_price = close_price
            position.profit_loss = profit_loss
            self.session.add(position)
            await self.session.commit()
            return position
            
        return None