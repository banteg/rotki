"""Repository for asset management"""

from typing import Optional

from sqlalchemy import delete, exists, select

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.orm.models import Asset as AssetModel
from rotkehlchen.db.orm.repositories.base import BaseRepository


class AssetRepository(BaseRepository[AssetModel]):
    """Repository for managing asset identifiers"""
    
    def __init__(self, session):
        super().__init__(session, AssetModel)
    
    def add_asset_id(self, asset_id: str) -> AssetModel:
        """Add an asset identifier"""
        asset = AssetModel(identifier=asset_id)
        return self.add(asset)
    
    def add_asset_ids(self, asset_ids: list[str]) -> list[AssetModel]:
        """Add multiple asset identifiers"""
        assets = [AssetModel(identifier=asset_id) for asset_id in asset_ids]
        return self.add_all(assets)
    
    def asset_exists(self, asset_id: str) -> bool:
        """Check if an asset identifier exists"""
        return self.exists(identifier=asset_id)
    
    def get_asset(self, asset_id: str) -> Optional[AssetModel]:
        """Get an asset by identifier"""
        return self.get(identifier=asset_id)
    
    def delete_asset_id(self, asset_id: str) -> bool:
        """Delete an asset identifier"""
        return self.delete_by(identifier=asset_id) > 0
    
    def get_all_asset_ids(self) -> list[str]:
        """Get all asset identifiers"""
        assets = self.get_all()
        return [asset.identifier for asset in assets]
    
    def replace_asset_id(self, old_id: str, new_id: str) -> bool:
        """Replace an asset identifier"""
        # Check if old exists and new doesn't
        if not self.asset_exists(old_id) or self.asset_exists(new_id):
            return False
        
        # Delete old and add new in same transaction
        self.delete_asset_id(old_id)
        self.add_asset_id(new_id)
        return True
    
    def ensure_assets_exist(self, asset_ids: list[str]) -> None:
        """Ensure multiple asset identifiers exist"""
        for asset_id in asset_ids:
            if not self.asset_exists(asset_id):
                self.add_asset_id(asset_id)
    
    def sync_assets(self, asset_ids: list[str]) -> tuple[list[str], list[str]]:
        """
        Sync asset identifiers with provided list.
        Returns (added_ids, removed_ids)
        """
        existing_ids = set(self.get_all_asset_ids())
        new_ids = set(asset_ids)
        
        # Find differences
        to_add = new_ids - existing_ids
        to_remove = existing_ids - new_ids
        
        # Add new assets
        if to_add:
            self.add_asset_ids(list(to_add))
        
        # Remove old assets
        for asset_id in to_remove:
            self.delete_asset_id(asset_id)
        
        return list(to_add), list(to_remove)
    
    def count_assets(self) -> int:
        """Get total count of assets"""
        return self.count()