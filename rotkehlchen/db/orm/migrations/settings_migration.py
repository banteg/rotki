"""Migration for settings and configuration data"""

from typing import Any

from sqlalchemy.orm import Session

from rotkehlchen.db.orm.migrations.migrator import BaseMigrationStep
from rotkehlchen.db.orm.models import Cache, DBSettings
from rotkehlchen.db.orm.repositories import CacheRepository, SettingsRepository


class SettingsMigration(BaseMigrationStep):
    """Migrate settings table"""

    @property
    def name(self) -> str:
        return 'settings'

    @property
    def description(self) -> str:
        return 'Migrate user settings and preferences'

    def migrate(self, old_conn: Any, new_session: Session) -> None:
        """Migrate settings data"""
        settings_repo = SettingsRepository(new_session)

        # Query old settings
        cursor = old_conn.cursor()
        cursor.execute('SELECT name, value FROM settings')

        for row in cursor:
            name, value = row
            settings_repo.set_setting(name, value)

        new_session.commit()

    def verify(self, old_conn: Any, new_session: Session) -> bool:
        """Verify settings migration"""
        cursor = old_conn.cursor()
        old_count = cursor.execute('SELECT COUNT(*) FROM settings').fetchone()[0]

        new_count = new_session.query(DBSettings).count()

        return old_count == new_count


class CacheMigration(BaseMigrationStep):
    """Migrate general cache table"""

    @property
    def name(self) -> str:
        return 'cache'

    @property
    def description(self) -> str:
        return 'Migrate general cache entries'

    def migrate(self, old_conn: Any, new_session: Session) -> None:
        """Migrate cache data"""
        cache_repo = CacheRepository(new_session)

        # Query old cache
        cursor = old_conn.cursor()
        cursor.execute('SELECT name, value, last_queried_ts FROM general_cache')

        for row in cursor:
            name, value, last_queried_ts = row
            cache_repo.set_cache(name, value, last_queried_ts)

        new_session.commit()

    def verify(self, old_conn: Any, new_session: Session) -> bool:
        """Verify cache migration"""
        cursor = old_conn.cursor()
        old_count = cursor.execute('SELECT COUNT(*) FROM general_cache').fetchone()[0]

        new_count = new_session.query(Cache).count()

        return old_count == new_count
