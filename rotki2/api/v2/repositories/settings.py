"""Repository for managing application settings."""
from typing import Any

from sqlmodel import select

from rotki2.api.v2.repositories.base import BaseRepository
from rotki2.db.models.user.cache import MultiSettings
from rotki2.db.models.user.models import Settings


class SettingsRepository(BaseRepository[Settings]):
    """Repository for managing application settings."""

    model = Settings

    def get_setting(self, name: str) -> Any | None:
        """Get a single setting value."""
        query = select(self.model).where(self.model.name == name)
        result = self.session.exec(query).first()
        return result.value if result else None

    def set_setting(self, name: str, value: Any) -> Settings:
        """Set or update a setting value."""
        setting = self.session.exec(
            select(self.model).where(self.model.name == name),
        ).first()

        if setting:
            setting.value = value
            self.session.add(setting)
        else:
            setting = Settings(name=name, value=value)
            self.session.add(setting)

        self.session.commit()
        return setting

    def delete_setting(self, name: str) -> bool:
        """Delete a setting."""
        query = select(self.model).where(self.model.name == name)
        setting = self.session.exec(query).first()

        if setting:
            self.session.delete(setting)
            self.session.commit()
            return True
        return False

    def get_all_settings(self) -> dict[str, Any]:
        """Get all settings as a dictionary."""
        settings = self.session.exec(select(self.model)).all()
        return {s.name: s.value for s in settings}

    def update_settings(self, settings_dict: dict[str, Any]) -> dict[str, Settings]:
        """Update multiple settings at once."""
        updated = {}

        for name, value in settings_dict.items():
            setting = self.set_setting(name, value)
            updated[name] = setting

        return updated

    # Common settings convenience methods

    def get_main_currency(self) -> str:
        """Get the main currency setting."""
        return self.get_setting('main_currency') or 'USD'

    def set_main_currency(self, currency: str) -> Settings:
        """Set the main currency."""
        return self.set_setting('main_currency', currency)

    def get_ui_floating_precision(self) -> int:
        """Get the UI floating precision setting."""
        return self.get_setting('ui_floating_precision') or 2

    def set_ui_floating_precision(self, precision: int) -> Settings:
        """Set the UI floating precision."""
        return self.set_setting('ui_floating_precision', precision)

    def get_active_modules(self) -> list[str]:
        """Get the list of active modules."""
        return self.get_setting('active_modules') or []

    def set_active_modules(self, modules: list[str]) -> Settings:
        """Set the list of active modules."""
        return self.set_setting('active_modules', modules)

    def is_module_active(self, module_name: str) -> bool:
        """Check if a specific module is active."""
        active_modules = self.get_active_modules()
        return module_name in active_modules

    def get_ignored_assets(self) -> list[str]:
        """Get the list of ignored assets."""
        return self.get_setting('ignored_assets') or []

    def set_ignored_assets(self, assets: list[str]) -> Settings:
        """Set the list of ignored assets."""
        return self.set_setting('ignored_assets', assets)


class MultiSettingsRepository(BaseRepository[MultiSettings]):
    """Repository for managing multi-value settings."""

    model = MultiSettings

    def get_values(self, name: str) -> list[Any]:
        """Get all values for a multi-setting."""
        query = select(self.model).where(self.model.name == name)
        results = self.session.exec(query).all()
        return [r.value for r in results]

    def add_value(self, name: str, value: Any) -> MultiSettings:
        """Add a value to a multi-setting."""
        # Check if value already exists
        existing = self.session.exec(
            select(self.model).where(
                self.model.name == name,
                self.model.value == value,
            ),
        ).first()

        if existing:
            return existing

        setting = MultiSettings(name=name, value=value)
        self.session.add(setting)
        self.session.commit()
        return setting

    def remove_value(self, name: str, value: Any) -> bool:
        """Remove a value from a multi-setting."""
        query = select(self.model).where(
            self.model.name == name,
            self.model.value == value,
        )
        setting = self.session.exec(query).first()

        if setting:
            self.session.delete(setting)
            self.session.commit()
            return True
        return False

    def clear_all_values(self, name: str) -> int:
        """Clear all values for a multi-setting."""
        query = select(self.model).where(self.model.name == name)
        settings = self.session.exec(query).all()

        count = len(settings)
        for setting in settings:
            self.session.delete(setting)

        if count > 0:
            self.session.commit()

        return count

    def set_values(self, name: str, values: list[Any]) -> list[MultiSettings]:
        """Replace all values for a multi-setting."""
        # Clear existing values
        self.clear_all_values(name)

        # Add new values
        settings = []
        for value in values:
            setting = self.add_value(name, value)
            settings.append(setting)

        return settings
