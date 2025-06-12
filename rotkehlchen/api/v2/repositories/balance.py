"""Balance repository for v2 API.

Handles all database operations related to balances.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.user.models import ManuallyTrackedBalance


class BalanceRepository(BaseRepository[ManuallyTrackedBalance]):
    """Repository for balance-related database operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, ManuallyTrackedBalance)
    
    def find_by_asset(self, asset_id: str) -> list[ManuallyTrackedBalance]:
        """Find all balances for a specific asset."""
        statement = select(ManuallyTrackedBalance).where(
            ManuallyTrackedBalance.asset == asset_id
        )
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_label(self, label: str) -> list[ManuallyTrackedBalance]:
        """Find all balances for a specific label."""
        statement = select(ManuallyTrackedBalance).where(
            ManuallyTrackedBalance.label == label
        )
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_location(self, location: str) -> list[ManuallyTrackedBalance]:
        """Find all balances for a specific location."""
        statement = select(ManuallyTrackedBalance).where(
            ManuallyTrackedBalance.location == location
        )
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_current_balances(self) -> list[ManuallyTrackedBalance]:
        """Find all current balances."""
        # Note: ManuallyTrackedBalance doesn't have timestamp field
        # Return all balances for now
        statement = select(ManuallyTrackedBalance)
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_timestamp_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[ManuallyTrackedBalance]:
        """Find balances within a timestamp range."""
        # Note: ManuallyTrackedBalance doesn't have timestamp field
        # Return empty list for now
        return []
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by(self, **kwargs) -> list[ManuallyTrackedBalance]:
        """Find balances by multiple criteria."""
        statement = select(ManuallyTrackedBalance)
        
        for key, value in kwargs.items():
            if hasattr(ManuallyTrackedBalance, key):
                statement = statement.where(getattr(ManuallyTrackedBalance, key) == value)
        
        results = self.session.exec(statement)
        return list(results.all())
    
    def update_balance(
        self,
        asset: str,
        label: str,
        location: str,
        amount: str,
        usd_value: str,
        timestamp: Optional[datetime] = None,
    ) -> ManuallyTrackedBalance:
        """Update or create a balance entry."""
        # Check if balance exists
        statement = select(ManuallyTrackedBalance).where(
            (ManuallyTrackedBalance.asset == asset) &
            (ManuallyTrackedBalance.label == label) &
            (ManuallyTrackedBalance.location == location)
        )
        result = self.session.exec(statement)
        balance = result.first()
        
        if balance:
            # Update existing
            balance.amount = amount
        else:
            # Create new
            balance = ManuallyTrackedBalance(
                asset=asset,
                label=label,
                location=location,
                amount=amount,
                category='A',  # Default category
            )
            self.session.add(balance)
        
        self.session.commit()
        self.session.refresh(balance)
        return balance