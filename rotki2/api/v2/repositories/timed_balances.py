"""Repository for timed balances and location data."""
from typing import TYPE_CHECKING

from sqlalchemy import select, text
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.models import TimedBalance, Timed'Location'Data

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from rotkehlchen.types import 'Location', 'Timestamp'


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


class Timed'Location'DataRepository(AsyncBaseRepository[Timed'Location'Data]):
    """Repository for handling timed location data."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, Timed'Location'Data)

    async def get_location_data_at_timestamp(
        self,
        timestamp: int,
    ) -> list[Timed'Location'Data]:
        """Get all location data at a specific timestamp.
        
        Args:
            timestamp: The timestamp to query
            
        Returns:
            List of timed location data at the timestamp
        """
        result = await self.session.exec(
            select(Timed'Location'Data).where(
                col(Timed'Location'Data.timestamp) == timestamp
            )
        )
        return list(result.all())

    async def get_location_history(
        self,
        location: str,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[Timed'Location'Data]:
        """Get location data history for a specific location.
        
        Args:
            location: The location identifier
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of timed location data
        """
        query = select(Timed'Location'Data).where(
            col(Timed'Location'Data.location) == location
        )
        
        if start_timestamp is not None:
            query = query.where(col(Timed'Location'Data.timestamp) >= start_timestamp)
        if end_timestamp is not None:
            query = query.where(col(Timed'Location'Data.timestamp) <= end_timestamp)
            
        query = query.order_by(Timed'Location'Data.timestamp)
        
        result = await self.session.exec(query)
        return list(result.all())
    
    async def get_last_balance_save_time(self) -> ''Timestamp' | None':
        """Get the timestamp of the last balance save.
        
        Returns:
            Last balance save timestamp or None if no balances saved
        """
        result = await self.session.exec(
            text("SELECT MAX(timestamp) FROM timed_balances")
        )
        timestamp = result.scalar()
        return 'Timestamp'(timestamp) if timestamp else None
    
    async def add_multiple_balances(
        self,
        balances: list[TimedBalance],
    ) -> None:
        """Add multiple timed balances efficiently.
        
        Args:
            balances: List of timed balances to add
        """
        if not balances:
            return
            
        # Use bulk insert for efficiency
        self.session.add_all(balances)
        await self.session.commit()
    
    async def query_timed_balances(
        self,
        from_ts: 'Timestamp' | None = None,
        to_ts: 'Timestamp' | None = None,
        currency: str | None = None,
        balance_type: str | None = None,
        infer_zero_balances: bool = True,
    ) -> list[TimedBalance]:
        """Query timed balances with advanced filtering.
        
        Args:
            from_ts: Start timestamp
            to_ts: End timestamp 
            currency: Optional currency filter
            balance_type: Optional balance type filter
            infer_zero_balances: Whether to infer zero balance periods
            
        Returns:
            List of timed balances
        """
        query = select(TimedBalance)
        
        if from_ts is not None:
            query = query.where(col(TimedBalance.timestamp) >= from_ts)
        if to_ts is not None:
            query = query.where(col(TimedBalance.timestamp) <= to_ts)
        if currency is not None:
            query = query.where(col(TimedBalance.currency) == currency)
        if balance_type is not None:
            query = query.where(col(TimedBalance.category) == balance_type)
            
        query = query.order_by(TimedBalance.timestamp, TimedBalance.currency)
        
        result = await self.session.exec(query)
        balances = list(result.all())
        
        if infer_zero_balances and balances:
            # Add zero balance inference logic
            balances = await self._infer_zero_timed_balances(balances, from_ts, to_ts)
            
        return balances
    
    async def _infer_zero_timed_balances(
        self,
        balances: list[TimedBalance],
        from_ts: 'Timestamp' | None,
        to_ts: 'Timestamp' | None,
    ) -> list[TimedBalance]:
        """Infer zero balances for periods without data.
        
        This is important for accurate balance charts.
        """
        # Group balances by currency
        from collections import defaultdict
        currency_balances = defaultdict(list)
        
        for balance in balances:
            currency_balances[balance.currency].append(balance)
            
        # Sort each currency's balances by timestamp
        for currency in currency_balances:
            currency_balances[currency].sort(key=lambda b: b.timestamp)
            
        # TODO: Implement zero balance inference logic
        # This would add zero balance entries between gaps
        
        return balances
    
    async def get_assets_with_balances(
        self,
        timestamp: 'Timestamp' | None = None,
    ) -> list[str]:
        """Get list of assets that have balance entries.
        
        Args:
            timestamp: Optional timestamp to check for balances at
            
        Returns:
            List of asset identifiers
        """
        if timestamp:
            query = text(
                "SELECT DISTINCT currency FROM timed_balances WHERE timestamp = :ts"
            )
            result = await self.session.execute(query, {"ts": timestamp})
        else:
            query = text("SELECT DISTINCT currency FROM timed_balances")
            result = await self.session.execute(query)
            
        return [row[0] for row in result.fetchall()]
    
    async def save_balances_snapshot(
        self,
        timestamp: 'Timestamp',
        asset_balances: dict[str, dict[str, str]],
        location_data: dict['Location', str],
    ) -> None:
        """Save a complete balance snapshot.
        
        Args:
            timestamp: The snapshot timestamp
            asset_balances: Dict of {asset: {"amount": str, "usd_value": str}}
            location_data: Dict of {location: total_usd_value}
        """
        # Save asset balances
        balances = []
        for asset, data in asset_balances.items():
            balance = TimedBalance(
                timestamp=timestamp,
                currency=asset,
                category="A",  # Default category
                amount=data.get("amount"),
                usd_value=data.get("usd_value"),
            )
            balances.append(balance)
            
        await self.add_multiple_balances(balances)
        
        # Save location data
        location_repo = Timed'Location'DataRepository(self.session)
        for location, usd_value in location_data.items():
            loc_data = Timed'Location'Data(
                timestamp=timestamp,
                location=location.value,
                usd_value=usd_value,
            )
            await location_repo.create(loc_data)