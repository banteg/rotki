"""Asset ignore repository for v2 API.

Handles operations for ignored assets.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotkehlchen.assets.asset import Asset
from rotki2.db.models.user.cache import MultiSettings
from rotki2.db.models.user.history import HistoryEvent


class AssetIgnoreRepository(AsyncBaseRepository[MultiSettings]):
    """Repository for ignored asset operations."""

    def __init__(self, session: AsyncSession):
        # Use MultiSetting as the model but filter for ignored_asset entries
        super().__init__(session, MultiSettings)

    async def add_ignored_asset(self, asset: Asset) -> None:
        """Add an asset to the ignored list and update history events."""
        # Add to ignored assets
        setting = MultiSettings(name='ignored_asset', value=asset.identifier)
        self.session.add(setting)  # SQLAlchemy will handle duplicates on commit

        # Update history events
        stmt = (
            select(HistoryEvent)
            .where(HistoryEvent.asset == asset.identifier)
        )
        result = await self.session.execute(stmt)
        events = result.scalars().all()
        for event in events:
            event.ignored = 1
            self.session.add(event)

        await self.session.commit()

    async def add_ignored_assets(self, assets: list[str]) -> None:
        """Add multiple assets to the ignored list."""
        for asset_id in assets:
            setting = MultiSettings(name='ignored_asset', value=asset_id)
            self.session.add(setting)

        # Update history events
        stmt = (
            select(HistoryEvent)
            .where(HistoryEvent.asset.in_(assets))
        )
        result = await self.session.execute(stmt)
        events = result.scalars().all()
        for event in events:
            event.ignored = 1
            self.session.add(event)

        await self.session.commit()

    async def remove_ignored_asset(self, asset: Asset) -> None:
        """Remove an asset from the ignored list and update history events."""
        # Remove from ignored assets
        stmt = select(MultiSettings).where(
            (MultiSettings.name == 'ignored_asset') &
            (MultiSettings.value == asset.identifier),
        )
        result = await self.session.execute(stmt)
        setting = result.scalars().first()
        if setting:
            await self.session.delete(setting)

        # Update history events
        stmt = (
            select(HistoryEvent)
            .where(HistoryEvent.asset == asset.identifier)
        )
        result = await self.session.execute(stmt)
        events = result.scalars().all()
        for event in events:
            event.ignored = 0
            self.session.add(event)

        await self.session.commit()

    async def get_ignored_assets(self) -> list[str]:
        """Get all ignored asset identifiers."""
        stmt = select(MultiSettings).where(MultiSettings.name == 'ignored_asset')
        result = await self.session.execute(stmt)
        settings = result.scalars().all()
        return [setting.value for setting in settings]

    async def is_asset_ignored(self, asset_id: str) -> bool:
        """Check if an asset is ignored."""
        stmt = select(MultiSettings).where(
            (MultiSettings.name == 'ignored_asset') &
            (MultiSettings.value == asset_id),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None

    async def find_by(self, **kwargs) -> list[MultiSettings]:
        """Find settings by criteria."""
        stmt = select(MultiSettings).where(MultiSettings.name == 'ignored_asset')

        if 'value' in kwargs:
            stmt = stmt.where(MultiSettings.value == kwargs['value'])

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
