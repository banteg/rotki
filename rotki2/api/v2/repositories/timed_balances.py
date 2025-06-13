"""Repository for timed balances and location data."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.models import TimedBalance, TimedLocationData

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TimedBalancesRepository(AsyncBaseRepository[TimedBalance]):
    """Repository for handling timed balance snapshots."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, TimedBalance)

    async def get_balances_at_timestamp(self, timestamp: int) -> list[TimedBalance]:
        """Get all balances at a specific timestamp.
        
        Args:
            timestamp: The timestamp to query
            
        Returns:
            List of timed balances at the timestamp
        """
        result = await self.session.exec(
            select(TimedBalance).where(
                col(TimedBalance.timestamp) == timestamp
            )
        )
        return list(result.all())

    async def get_balance_history(
        self,
        currency: str,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[TimedBalance]:
        """Get balance history for a specific currency.
        
        Args:
            currency: The currency/asset identifier
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of timed balances for the currency
        """
        query = select(TimedBalance).where(
            col(TimedBalance.currency) == currency
        )
        
        if start_timestamp is not None:
            query = query.where(col(TimedBalance.timestamp) >= start_timestamp)
        if end_timestamp is not None:
            query = query.where(col(TimedBalance.timestamp) <= end_timestamp)
            
        query = query.order_by(TimedBalance.timestamp)
        
        result = await self.session.exec(query)
        return list(result.all())


class TimedLocationDataRepository(AsyncBaseRepository[TimedLocationData]):
    """Repository for handling timed location data."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, TimedLocationData)

    async def get_location_data_at_timestamp(
        self,
        timestamp: int,
    ) -> list[TimedLocationData]:
        """Get all location data at a specific timestamp.
        
        Args:
            timestamp: The timestamp to query
            
        Returns:
            List of timed location data at the timestamp
        """
        result = await self.session.exec(
            select(TimedLocationData).where(
                col(TimedLocationData.timestamp) == timestamp
            )
        )
        return list(result.all())

    async def get_location_history(
        self,
        location: str,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[TimedLocationData]:
        """Get location data history for a specific location.
        
        Args:
            location: The location identifier
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of timed location data
        """
        query = select(TimedLocationData).where(
            col(TimedLocationData.location) == location
        )
        
        if start_timestamp is not None:
            query = query.where(col(TimedLocationData.timestamp) >= start_timestamp)
        if end_timestamp is not None:
            query = query.where(col(TimedLocationData.timestamp) <= end_timestamp)
            
        query = query.order_by(TimedLocationData.timestamp)
        
        result = await self.session.exec(query)
        return list(result.all())