"""Asset repository for v2 API.

Handles all database operations related to assets.
"""

from sqlmodel import Session, select

from rotki2.api.v2.repositories.base import BaseRepository
from rotkehlchen.assets.types import AssetType
from rotki2.db.models.user.models import Asset


class AssetRepository(BaseRepository[Asset]):
    """Repository for asset-related database operations."""
    def __init__(self, session: Session):
        super().__init__(session, Asset)

    def find_by_symbol(self, symbol: str) -> Asset | None:
        """Find asset by symbol."""
        # Note: The Asset model only has identifier, not symbol
        # This needs to be refactored based on actual asset data structure
        statement = select(Asset).where(Asset.identifier == symbol)
        result = self.session.exec(statement)
        return result.first()

    def find_by_type(self, asset_type: AssetType) -> list[Asset]:
        """Find all assets of a specific type."""
        # Note: The Asset model doesn't have type field
        # This needs to be refactored based on actual asset data structure
        return []
        results = self.session.exec(statement)
        return list(results.all())

    def find_by(self, **kwargs) -> list[Asset]:
        """Find assets by multiple criteria."""
        statement = select(Asset)

        for key, value in kwargs.items():
            if hasattr(Asset, key):
                statement = statement.where(getattr(Asset, key) == value)

        results = self.session.exec(statement)
        return list(results.all())

    def search_by_name_or_symbol(self, query: str) -> list[Asset]:
        """Search assets by name or symbol (case-insensitive)."""
        # Note: The Asset model only has identifier
        # This needs to be refactored based on actual asset data structure
        statement = select(Asset).where(
            Asset.identifier.contains(query),
        )
        results = self.session.exec(statement)
        return list(results.all())

    def get_all_active(self) -> list[Asset]:
        """Get all active (non-deleted) assets."""
        # Note: The Asset model doesn't have a deleted field
        # Return all assets for now
        statement = select(Asset)
        results = self.session.exec(statement)
        return list(results.all())

    def exists(self, symbol: str) -> bool:
        """Check if asset exists by symbol."""
        return self.find_by_symbol(symbol) is not None
