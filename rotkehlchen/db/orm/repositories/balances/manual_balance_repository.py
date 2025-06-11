"""Repository for manually tracked balances"""

from typing import Optional

from sqlalchemy import delete, select

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance as ManuallyTrackedBalanceData
from rotkehlchen.db.orm.models import ManuallyTrackedBalance
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location


class ManualBalanceRepository(BaseRepository[ManuallyTrackedBalance]):
    """Repository for managing manually tracked balances"""
    
    def __init__(self, session):
        super().__init__(session, ManuallyTrackedBalance)
    
    def add_balance(
        self,
        asset: Asset,
        label: str,
        amount: FVal,
        location: Location,
        category: BalanceType = BalanceType.ASSET,
    ) -> ManuallyTrackedBalance:
        """Add a manually tracked balance"""
        balance = ManuallyTrackedBalance(
            asset=asset.identifier,
            label=label,
            amount=str(amount),
            location=location.serialize_for_db(),
            category=category.serialize_for_db(),
        )
        return self.add(balance)
    
    def get_balances(
        self,
        asset: Optional[Asset] = None,
        label: Optional[str] = None,
        location: Optional[Location] = None,
        category: Optional[BalanceType] = None,
    ) -> list[ManuallyTrackedBalance]:
        """Get manually tracked balances with optional filters"""
        filters = {}
        
        if asset is not None:
            filters['asset'] = asset.identifier
        if label is not None:
            filters['label'] = label
        if location is not None:
            filters['location'] = location.serialize_for_db()
        if category is not None:
            filters['category'] = category.serialize_for_db()
        
        return self.get_all(**filters)
    
    def update_balance(
        self,
        balance_id: int,
        amount: Optional[FVal] = None,
        label: Optional[str] = None,
        location: Optional[Location] = None,
        category: Optional[BalanceType] = None,
    ) -> Optional[ManuallyTrackedBalance]:
        """Update a manually tracked balance"""
        balance = self.get(id=balance_id)
        if not balance:
            return None
        
        if amount is not None:
            balance.amount = str(amount)
        if label is not None:
            balance.label = label
        if location is not None:
            balance.location = location.serialize_for_db()
        if category is not None:
            balance.category = category.serialize_for_db()
        
        return self.update(balance)
    
    def delete_balance(self, balance_id: int) -> bool:
        """Delete a manually tracked balance"""
        return self.delete_by(id=balance_id) > 0
    
    def delete_balances_by_asset(self, asset: Asset) -> int:
        """Delete all balances for an asset"""
        return self.delete_by(asset=asset.identifier)
    
    def get_balances_by_location(
        self,
        location: Location,
    ) -> list[ManuallyTrackedBalance]:
        """Get all balances for a specific location"""
        return self.get_all(location=location.serialize_for_db())
    
    def to_domain_model(
        self,
        balance: ManuallyTrackedBalance,
    ) -> ManuallyTrackedBalanceData:
        """Convert database model to domain model"""
        return ManuallyTrackedBalanceData(
            id=balance.id,
            asset=Asset(balance.asset),
            label=balance.label,
            amount=FVal(balance.amount) if balance.amount else FVal(0),
            location=Location.deserialize_from_db(balance.location),
            tags=None,  # Tags would be loaded separately
            balance_type=BalanceType.deserialize_from_db(balance.category),
        )
    
    def add_multiple_balances(
        self,
        balances: list[ManuallyTrackedBalanceData],
    ) -> list[ManuallyTrackedBalance]:
        """Add multiple manually tracked balances"""
        db_balances = []
        
        for balance_data in balances:
            balance = ManuallyTrackedBalance(
                asset=balance_data.asset.identifier,
                label=balance_data.label,
                amount=str(balance_data.amount),
                location=balance_data.location.serialize_for_db(),
                category=balance_data.balance_type.serialize_for_db(),
            )
            db_balances.append(balance)
        
        return self.add_all(db_balances)
    
    def get_total_by_asset(
        self,
        asset: Asset,
        category: Optional[BalanceType] = None,
    ) -> FVal:
        """Get total amount for an asset across all manual balances"""
        from sqlalchemy import func
        
        query = select(func.sum(ManuallyTrackedBalance.amount)).filter_by(
            asset=asset.identifier
        )
        
        if category is not None:
            query = query.filter_by(category=category.serialize_for_db())
        
        result = self.session.execute(query).scalar()
        return FVal(result) if result else FVal(0)
    
    def get_all_locations(self) -> list[Location]:
        """Get all unique locations from manual balances"""
        query = select(ManuallyTrackedBalance.location).distinct()
        locations = self.session.execute(query).scalars().all()
        
        return [Location.deserialize_from_db(loc) for loc in locations]