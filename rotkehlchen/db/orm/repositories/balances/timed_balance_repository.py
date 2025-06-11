"""Repository for timed balance snapshots"""

from typing import Optional

from sqlalchemy import and_, delete, func, select

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.orm.models import TimedBalance, TimedLocationData
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp


class TimedBalanceRepository(BaseRepository[TimedBalance]):
    """Repository for managing timed balance snapshots"""
    
    def __init__(self, session):
        super().__init__(session, TimedBalance)
    
    def add_balance_snapshot(
        self,
        timestamp: Timestamp,
        asset: Asset,
        amount: FVal,
        usd_value: FVal,
        category: BalanceType = BalanceType.ASSET,
    ) -> TimedBalance:
        """Add a single balance snapshot"""
        balance = TimedBalance(
            timestamp=int(timestamp),
            currency=asset.identifier,
            amount=str(amount),
            usd_value=str(usd_value),
            category=category.serialize_for_db(),
        )
        return self.add(balance)
    
    def add_multiple_balances(
        self,
        timestamp: Timestamp,
        balances: list[tuple[Asset, Balance]],
    ) -> list[TimedBalance]:
        """Add multiple balance snapshots at once"""
        db_balances = []
        
        for asset, balance in balances:
            # Add asset balance
            if balance.amount > 0:
                db_balance = TimedBalance(
                    timestamp=int(timestamp),
                    currency=asset.identifier,
                    amount=str(balance.amount),
                    usd_value=str(balance.usd_value),
                    category=BalanceType.ASSET.serialize_for_db(),
                )
                db_balances.append(db_balance)
        
        return self.add_all(db_balances) if db_balances else []
    
    def get_balances_at_timestamp(
        self,
        timestamp: Timestamp,
        asset: Optional[Asset] = None,
        category: Optional[BalanceType] = None,
    ) -> list[TimedBalance]:
        """Get balance snapshots at a specific timestamp"""
        filters = {'timestamp': int(timestamp)}
        
        if asset is not None:
            filters['currency'] = asset.identifier
        if category is not None:
            filters['category'] = category.serialize_for_db()
        
        return self.get_all(**filters)
    
    def get_latest_balance(
        self,
        asset: Asset,
        category: BalanceType = BalanceType.ASSET,
    ) -> Optional[TimedBalance]:
        """Get the latest balance for an asset"""
        stmt = (
            select(TimedBalance)
            .filter_by(
                currency=asset.identifier,
                category=category.serialize_for_db(),
            )
            .order_by(TimedBalance.timestamp.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_balance_history(
        self,
        asset: Asset,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
        category: BalanceType = BalanceType.ASSET,
    ) -> list[TimedBalance]:
        """Get balance history for an asset within a time range"""
        stmt = select(TimedBalance).filter_by(
            currency=asset.identifier,
            category=category.serialize_for_db(),
        )
        
        if from_timestamp is not None:
            stmt = stmt.filter(TimedBalance.timestamp >= int(from_timestamp))
        if to_timestamp is not None:
            stmt = stmt.filter(TimedBalance.timestamp <= int(to_timestamp))
        
        stmt = stmt.order_by(TimedBalance.timestamp)
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_unique_timestamps(
        self,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
    ) -> list[Timestamp]:
        """Get all unique timestamps in the balance history"""
        stmt = select(TimedBalance.timestamp).distinct()
        
        if from_timestamp is not None:
            stmt = stmt.filter(TimedBalance.timestamp >= int(from_timestamp))
        if to_timestamp is not None:
            stmt = stmt.filter(TimedBalance.timestamp <= int(to_timestamp))
        
        stmt = stmt.order_by(TimedBalance.timestamp)
        
        results = self.session.execute(stmt).scalars().all()
        return [Timestamp(ts) for ts in results]
    
    def delete_balances_before(
        self,
        timestamp: Timestamp,
        asset: Optional[Asset] = None,
    ) -> int:
        """Delete balance snapshots before a timestamp"""
        stmt = delete(TimedBalance).filter(
            TimedBalance.timestamp < int(timestamp)
        )
        
        if asset is not None:
            stmt = stmt.filter(TimedBalance.currency == asset.identifier)
        
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def get_netvalue_at_timestamps(
        self,
        timestamps: list[Timestamp],
        currency: AssetWithOracles = A_USD,
    ) -> list[tuple[Timestamp, FVal]]:
        """Get total netvalue at multiple timestamps"""
        results = []
        
        for timestamp in timestamps:
            # Sum all USD values at timestamp
            stmt = (
                select(func.sum(TimedBalance.usd_value))
                .filter_by(timestamp=int(timestamp))
            )
            total_usd = self.session.execute(stmt).scalar() or 0
            
            results.append((timestamp, FVal(total_usd)))
        
        return results
    
    def save_location_data(
        self,
        timestamp: Timestamp,
        location_data: dict[Location, Balance],
    ) -> None:
        """Save location data snapshot"""
        # Delete existing data at timestamp
        stmt = delete(TimedLocationData).filter_by(timestamp=int(timestamp))
        self.session.execute(stmt)
        
        # Add new location data
        for location, balance in location_data.items():
            if balance.usd_value > 0:
                location_entry = TimedLocationData(
                    timestamp=int(timestamp),
                    location=location.serialize_for_db(),
                    usd_value=str(balance.usd_value),
                )
                self.session.add(location_entry)
        
        self.session.flush()
    
    def get_location_data_at_timestamp(
        self,
        timestamp: Timestamp,
    ) -> dict[Location, FVal]:
        """Get location data at a specific timestamp"""
        stmt = select(TimedLocationData).filter_by(timestamp=int(timestamp))
        results = self.session.execute(stmt).scalars().all()
        
        location_data = {}
        for entry in results:
            location = Location.deserialize_from_db(entry.location)
            location_data[location] = FVal(entry.usd_value)
        
        return location_data
    
    def get_first_timestamp(self) -> Optional[Timestamp]:
        """Get the earliest timestamp in balance history"""
        stmt = select(func.min(TimedBalance.timestamp))
        result = self.session.execute(stmt).scalar()
        return Timestamp(result) if result else None
    
    def get_last_timestamp(self) -> Optional[Timestamp]:
        """Get the latest timestamp in balance history"""
        stmt = select(func.max(TimedBalance.timestamp))
        result = self.session.execute(stmt).scalar()
        return Timestamp(result) if result else None