"""Repository for managing application settings."""
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.cache import MultiSettings
from rotki2.db.models.user.models import Settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SettingsRepository(AsyncBaseRepository[Settings]):
    """Repository for managing application settings."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, Settings)

    async def get_setting(self, name: str) -> Any | None:
        """Get a single setting value."""
        result = await self.session.exec(
            select(Settings).where(col(Settings.name) == name)
        )
        setting = result.first()
        return setting.value if setting else None

    async def set_setting(self, name: str, value: Any) -> Settings:
        """Set or update a setting value."""
        # Use upsert pattern for settings
        stmt = text(
            "INSERT INTO settings (name, value) VALUES (:name, :value) "
            "ON CONFLICT(name) DO UPDATE SET value = :value"
        )
        await self.session.execute(stmt, {"name": name, "value": value})
        await self.session.commit()
        
        # Return the setting
        result = await self.session.exec(
            select(Settings).where(col(Settings.name) == name)
        )
        return result.first()

    async def delete_setting(self, name: str) -> bool:
        """Delete a setting."""
        result = await self.session.exec(
            select(Settings).where(col(Settings.name) == name)
        )
        setting = result.first()

        if setting:
            await self.session.delete(setting)
            await self.session.commit()
            return True
        return False

    async def get_all_settings(self) -> dict[str, Any]:
        """Get all settings as a dictionary."""
        result = await self.session.exec(select(Settings))
        settings = result.all()
        return {s.name: s.value for s in settings}

    async def update_settings(self, settings_dict: dict[str, Any]) -> dict[str, Settings]:
        """Update multiple settings at once."""
        updated = {}

        for name, value in settings_dict.items():
            setting = await self.set_setting(name, value)
            updated[name] = setting

        return updated

    # Common settings convenience methods

    async def get_main_currency(self) -> str:
        """Get the main currency setting."""
        return await self.get_setting('main_currency') or 'USD'

    async def set_main_currency(self, currency: str) -> Settings:
        """Set the main currency."""
        return await self.set_setting('main_currency', currency)

    async def get_ui_floating_precision(self) -> int:
        """Get the UI floating precision setting."""
        return await self.get_setting('ui_floating_precision') or 2

    async def set_ui_floating_precision(self, precision: int) -> Settings:
        """Set the UI floating precision."""
        return await self.set_setting('ui_floating_precision', precision)

    async def get_active_modules(self) -> list[str]:
        """Get the list of active modules."""
        return await self.get_setting('active_modules') or []

    async def set_active_modules(self, modules: list[str]) -> Settings:
        """Set the list of active modules."""
        return await self.set_setting('active_modules', modules)

    async def is_module_active(self, module_name: str) -> bool:
        """Check if a specific module is active."""
        active_modules = await self.get_active_modules()
        return module_name in active_modules

    async def get_ignored_assets(self) -> list[str]:
        """Get the list of ignored assets."""
        return await self.get_setting('ignored_assets') or []

    async def set_ignored_assets(self, assets: list[str]) -> Settings:
        """Set the list of ignored assets."""
        return await self.set_setting('ignored_assets', assets)


class MultiSettingsRepository(AsyncBaseRepository[MultiSettings]):
    """Repository for managing multi-value settings."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, MultiSettings)

    async def get_values(self, name: str) -> list[Any]:
        """Get all values for a multi-setting."""
        result = await self.session.exec(
            select(MultiSettings).where(col(MultiSettings.name) == name)
        )
        results = result.all()
        return [r.value for r in results]

    async def add_value(self, name: str, value: Any) -> MultiSettings:
        """Add a value to a multi-setting."""
        # Check if value already exists
        result = await self.session.exec(
            select(MultiSettings).where(
                col(MultiSettings.name) == name,
                col(MultiSettings.value) == value,
            )
        )
        existing = result.first()

        if existing:
            return existing

        setting = MultiSettings(name=name, value=value)
        await self.create(setting)
        return setting

    async def remove_value(self, name: str, value: Any) -> bool:
        """Remove a value from a multi-setting."""
        result = await self.session.exec(
            select(MultiSettings).where(
                col(MultiSettings.name) == name,
                col(MultiSettings.value) == value,
            )
        )
        setting = result.first()

        if setting:
            await self.delete(setting)
            return True
        return False

    async def clear_all_values(self, name: str) -> int:
        """Clear all values for a multi-setting."""
        result = await self.session.exec(
            select(MultiSettings).where(col(MultiSettings.name) == name)
        )
        settings = result.all()

        count = len(settings)
        for setting in settings:
            await self.session.delete(setting)

        if count > 0:
            await self.session.commit()

        return count

    async def set_values(self, name: str, values: list[Any]) -> list[MultiSettings]:
        """Replace all values for a multi-setting."""
        # Clear existing values
        await self.clear_all_values(name)

        # Add new values
        settings = []
        for value in values:
            setting = await self.add_value(name, value)
            settings.append(setting)

        return settings
