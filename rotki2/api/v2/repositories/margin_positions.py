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

    async def get_positions_by_asset(
        self,
        asset: str,
        exchange: str | None = None,
    ) -> list[MarginPosition]:
        """Get all margin positions for a specific asset.
        
        Args:
            asset: The asset identifier
            exchange: Optional exchange filter
            
        Returns:
            List of margin positions
        """
        query = select(MarginPosition).where(
            col(MarginPosition.asset) == asset
        )
        
        if exchange:
            query = query.where(col(MarginPosition.exchange) == exchange)
            
        query = query.order_by(MarginPosition.open_time.desc())
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_positions_in_range(
        self,
        start_timestamp: int,
        end_timestamp: int,
        exchange: str | None = None,
    ) -> list[MarginPosition]:
        """Get margin positions opened within a timestamp range.
        
        Args:
            start_timestamp: Start of the time range
            end_timestamp: End of the time range
            exchange: Optional exchange filter
            
        Returns:
            List of margin positions
        """
        query = select(MarginPosition).where(
            col(MarginPosition.open_time) >= start_timestamp,
            col(MarginPosition.open_time) <= end_timestamp,
        )
        
        if exchange:
            query = query.where(col(MarginPosition.exchange) == exchange)
            
        query = query.order_by(MarginPosition.open_time)
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_total_profit_loss(
        self,
        exchange: str | None = None,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> dict[str, str]:
        """Calculate total profit/loss from closed positions.
        
        Args:
            exchange: Optional exchange filter
            start_timestamp: Optional start timestamp for close time
            end_timestamp: Optional end timestamp for close time
            
        Returns:
            Dict with total_profit_loss and position_count
        """
        from sqlalchemy import func
        
        query = select(
            func.sum(MarginPosition.profit_loss).label('total_profit_loss'),
            func.count(MarginPosition.identifier).label('position_count'),
        ).where(
            col(MarginPosition.close_time).is_not(None),
            col(MarginPosition.profit_loss).is_not(None),
        )
        
        if exchange:
            query = query.where(col(MarginPosition.exchange) == exchange)
        if start_timestamp:
            query = query.where(col(MarginPosition.close_time) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(MarginPosition.close_time) <= end_timestamp)
        
        result = await self.session.exec(query)
        row = result.first()
        
        return {
            'total_profit_loss': str(row[0] or 0),
            'position_count': str(row[1] or 0),
        }

    async def get_margin_summary_by_exchange(self) -> list[dict[str, str]]:
        """Get margin position summary grouped by exchange.
        
        Returns:
            List of dicts with exchange, open_count, closed_count, total_profit_loss
        """
        from sqlalchemy import case, func
        
        query = select(
            MarginPosition.exchange,
            func.sum(
                case(
                    (col(MarginPosition.close_time).is_(None), 1),
                    else_=0,
                )
            ).label('open_count'),
            func.sum(
                case(
                    (col(MarginPosition.close_time).is_not(None), 1),
                    else_=0,
                )
            ).label('closed_count'),
            func.sum(MarginPosition.profit_loss).label('total_profit_loss'),
        ).group_by(MarginPosition.exchange)
        
        result = await self.session.exec(query)
        
        return [
            {
                'exchange': row[0],
                'open_count': str(row[1] or 0),
                'closed_count': str(row[2] or 0),
                'total_profit_loss': str(row[3] or 0),
            }
            for row in result.all()
        ]