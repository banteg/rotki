"""Repository for owned assets tracking"""

from collections import defaultdict
from typing import Optional

from sqlalchemy import func, select

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.orm.models import Asset as AssetModel, ManuallyTrackedBalance, TimedBalance
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp


class OwnedAssetsRepository(BaseRepository[AssetModel]):
    """Repository for tracking user's owned assets and their distribution"""
    
    def __init__(self, session):
        super().__init__(session, AssetModel)
    
    def get_owned_assets(self) -> list[Asset]:
        """Get all assets owned by the user"""
        # Get assets from manually tracked balances
        manual_query = (
            select(ManuallyTrackedBalance.asset)
            .distinct()
        )
        manual_assets = self.session.execute(manual_query).scalars().all()
        
        # Get assets from timed balances
        timed_query = (
            select(TimedBalance.currency)
            .distinct()
        )
        timed_assets = self.session.execute(timed_query).scalars().all()
        
        # Combine and deduplicate
        all_asset_ids = set(manual_assets + timed_assets)
        
        # Convert to Asset objects
        assets = []
        for asset_id in all_asset_ids:
            try:
                assets.append(Asset(asset_id))
            except Exception:
                # Skip invalid assets
                pass
        
        return assets
    
    def get_latest_asset_value_distribution(self) -> list[dict]:
        """Get the latest value distribution of all assets"""
        # Get latest timestamp
        latest_ts_query = select(func.max(TimedBalance.timestamp))
        latest_timestamp = self.session.execute(latest_ts_query).scalar()
        
        if not latest_timestamp:
            return []
        
        # Get all balances at latest timestamp
        balances_query = (
            select(
                TimedBalance.currency,
                func.sum(TimedBalance.amount).label('total_amount'),
                func.sum(TimedBalance.usd_value).label('total_usd_value')
            )
            .filter(TimedBalance.timestamp == latest_timestamp)
            .group_by(TimedBalance.currency)
        )
        
        results = self.session.execute(balances_query).all()
        
        distribution = []
        for currency, amount, usd_value in results:
            if amount and usd_value:
                distribution.append({
                    'asset': currency,
                    'amount': str(amount),
                    'usd_value': str(usd_value),
                    'timestamp': latest_timestamp,
                })
        
        return sorted(distribution, key=lambda x: float(x['usd_value']), reverse=True)
    
    def get_latest_location_value_distribution(self) -> list[dict]:
        """Get the latest value distribution by location"""
        # Get latest timestamp
        latest_ts_query = select(func.max(TimedBalance.timestamp))
        latest_timestamp = self.session.execute(latest_ts_query).scalar()
        
        if not latest_timestamp:
            return []
        
        # Get location data from timed_location_data table
        from rotkehlchen.db.orm.models import TimedLocationData
        
        location_query = (
            select(
                TimedLocationData.location,
                TimedLocationData.usd_value,
            )
            .filter(TimedLocationData.timestamp == latest_timestamp)
        )
        
        results = self.session.execute(location_query).all()
        
        distribution = []
        for location_char, usd_value in results:
            if usd_value:
                location = Location.deserialize_from_db(location_char)
                distribution.append({
                    'location': location.serialize(),
                    'usd_value': str(usd_value),
                    'timestamp': latest_timestamp,
                })
        
        return sorted(distribution, key=lambda x: float(x['usd_value']), reverse=True)
    
    def get_assets_value_at_timestamp(
        self,
        timestamp: Timestamp,
        asset: Optional[Asset] = None,
    ) -> dict[str, FVal]:
        """Get asset values at a specific timestamp"""
        query = select(
            TimedBalance.currency,
            func.sum(TimedBalance.amount).label('total_amount'),
            func.sum(TimedBalance.usd_value).label('total_usd_value')
        ).filter(
            TimedBalance.timestamp == timestamp
        )
        
        if asset:
            query = query.filter(TimedBalance.currency == asset.identifier)
        
        query = query.group_by(TimedBalance.currency)
        
        results = self.session.execute(query).all()
        
        values = {}
        for currency, amount, usd_value in results:
            if amount and usd_value:
                values[currency] = {
                    'amount': FVal(amount),
                    'usd_value': FVal(usd_value),
                }
        
        return values
    
    def get_assets_with_balance(self) -> list[str]:
        """Get all assets that have a non-zero balance"""
        # From manually tracked balances
        manual_query = (
            select(ManuallyTrackedBalance.asset)
            .filter(ManuallyTrackedBalance.amount > 0)
            .distinct()
        )
        manual_assets = set(self.session.execute(manual_query).scalars().all())
        
        # From latest timed balances
        latest_ts_query = select(func.max(TimedBalance.timestamp))
        latest_timestamp = self.session.execute(latest_ts_query).scalar()
        
        timed_assets = set()
        if latest_timestamp:
            timed_query = (
                select(TimedBalance.currency)
                .filter(
                    TimedBalance.timestamp == latest_timestamp,
                    TimedBalance.amount > 0
                )
                .distinct()
            )
            timed_assets = set(self.session.execute(timed_query).scalars().all())
        
        return sorted(list(manual_assets | timed_assets))
    
    def update_owned_assets_in_global_db(self) -> list[str]:
        """
        Update the global database with owned assets.
        Returns list of asset identifiers that were added.
        """
        owned_assets = self.get_owned_assets()
        
        # This would interact with global DB - for now just return the identifiers
        return [asset.identifier for asset in owned_assets]