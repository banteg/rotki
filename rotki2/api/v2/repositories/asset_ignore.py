"""Asset ignore repository for v2 API.

Handles operations for ignored assets.
"""
from sqlmodel import Session, select

from rotki2.api.v2.repositories.base import BaseRepository
from rotkehlchen.assets.asset import Asset
from rotki2.db.models.user.cache import MultiSettings
from rotki2.db.models.user.history import HistoryEvent


class AssetIgnoreRepository(BaseRepository[MultiSettings]):
    """Repository for ignored asset operations."""

    def __init__(self, session: Session):
        # Use MultiSetting as the model but filter for ignored_asset entries
        super().__init__(session, MultiSettings)

    def add_ignored_asset(self, asset: Asset) -> None:
        """Add an asset to the ignored list and update history events."""
        # Add to ignored assets
        setting = MultiSettings(name='ignored_asset', value=asset.identifier)
        self.session.merge(setting)  # Use merge to handle duplicates

        # Update history events
        stmt = (
            select(HistoryEvent)
            .where(HistoryEvent.asset == asset.identifier)
        )
        events = self.session.exec(stmt).all()
        for event in events:
            event.ignored = 1
            self.session.add(event)

        self.session.commit()

    def add_ignored_assets(self, assets: list[str]) -> None:
        """Add multiple assets to the ignored list."""
        for asset_id in assets:
            setting = MultiSettings(name='ignored_asset', value=asset_id)
            self.session.merge(setting)

        # Update history events
        stmt = (
            select(HistoryEvent)
            .where(HistoryEvent.asset.in_(assets))
        )
        events = self.session.exec(stmt).all()
        for event in events:
            event.ignored = 1
            self.session.add(event)

        self.session.commit()

    def remove_ignored_asset(self, asset: Asset) -> None:
        """Remove an asset from the ignored list and update history events."""
        # Remove from ignored assets
        stmt = select(MultiSettings).where(
            (MultiSettings.name == 'ignored_asset') &
            (MultiSettings.value == asset.identifier),
        )
        setting = self.session.exec(stmt).first()
        if setting:
            self.session.delete(setting)

        # Update history events
        stmt = (
            select(HistoryEvent)
            .where(HistoryEvent.asset == asset.identifier)
        )
        events = self.session.exec(stmt).all()
        for event in events:
            event.ignored = 0
            self.session.add(event)

        self.session.commit()

    def get_ignored_assets(self) -> list[str]:
        """Get all ignored asset identifiers."""
        stmt = select(MultiSettings).where(MultiSettings.name == 'ignored_asset')
        results = self.session.exec(stmt).all()
        return [setting.value for setting in results]

    def is_asset_ignored(self, asset_id: str) -> bool:
        """Check if an asset is ignored."""
        stmt = select(MultiSettings).where(
            (MultiSettings.name == 'ignored_asset') &
            (MultiSettings.value == asset_id),
        )
        return self.session.exec(stmt).first() is not None

    def find_by(self, **kwargs) -> list[MultiSettings]:
        """Find settings by criteria."""
        stmt = select(MultiSettings).where(MultiSettings.name == 'ignored_asset')

        if 'value' in kwargs:
            stmt = stmt.where(MultiSettings.value == kwargs['value'])

        results = self.session.exec(stmt)
        return list(results.all())
