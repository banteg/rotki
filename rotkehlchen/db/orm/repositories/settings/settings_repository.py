"""Repository for application settings"""

from typing import Any

from rotkehlchen.db.orm.models import UserSettings
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.types import Timestamp


class SettingsRepository(BaseRepository[UserSettings]):
    """Repository for managing application settings"""

    def __init__(self, session):
        super().__init__(session, UserSettings)

    def get_setting(self, name: str) -> str | None:
        """Get a setting value by name"""
        setting = self.get(name=name)
        return setting.value if setting else None

    def get_version(self) -> int:
        """Get database version"""
        value = self.get_setting('version')
        if value is None:
            raise DBUpgradeError('No version in database')
        return int(value)

    def get_last_write_ts(self) -> Timestamp:
        """Get last write timestamp"""
        value = self.get_setting('last_write_ts')
        return Timestamp(int(value)) if value else Timestamp(0)

    def get_premium_should_sync(self) -> bool:
        """Get premium sync setting"""
        value = self.get_setting('premium_should_sync')
        return value == 'true' if value else False

    def get_main_currency(self) -> str:
        """Get main currency setting"""
        value = self.get_setting('main_currency')
        return value or 'USD'

    def get_last_data_migration(self) -> int | None:
        """Get last data migration version"""
        value = self.get_setting('last_data_migration')
        return int(value) if value else None

    def get_non_syncing_exchanges(self) -> list[str]:
        """Get list of non-syncing exchanges"""
        import json
        value = self.get_setting('non_syncing_exchanges')
        if not value:
            return []
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []

    def set_setting(self, name: str, value: Any) -> None:
        """Set a setting value"""
        # Convert value to string based on type
        if isinstance(value, bool):
            str_value = 'true' if value else 'false'
        elif isinstance(value, (list, dict)):
            import json
            str_value = json.dumps(value)
        else:
            str_value = str(value)

        # Update or create setting
        setting = self.get(name=name)
        if setting:
            setting.value = str_value
            self.update(setting)
        else:
            self.add(UserSettings(name=name, value=str_value))

    def set_version(self, version: int) -> None:
        """Set database version"""
        self.set_setting('version', version)

    def set_last_write_ts(self, timestamp: Timestamp) -> None:
        """Set last write timestamp"""
        self.set_setting('last_write_ts', int(timestamp))

    def delete_setting(self, name: str) -> bool:
        """Delete a setting"""
        setting = self.get(name=name)
        if setting:
            self.delete(setting)
            return True
        return False

    def get_all_settings(self) -> dict[str, str]:
        """Get all settings as a dictionary"""
        settings = self.get_all()
        return {s.name: s.value for s in settings if s.value is not None}

    def update_settings(self, settings: dict[str, Any]) -> None:
        """Update multiple settings at once"""
        for name, value in settings.items():
            self.set_setting(name, value)
