"""Repository for database info management"""


from sqlalchemy import select

from rotkehlchen.db.orm.models import DBInfo
from rotkehlchen.db.orm.repositories.base import BaseRepository


class DatabaseInfoRepository(BaseRepository[DBInfo]):
    """Repository for managing database metadata"""

    def __init__(self, session):
        super().__init__(session, DBInfo)

    def get_version(self) -> int | None:
        """Get database version"""
        info = self._get_info()
        return info.version if info else None

    def set_version(self, version: int) -> DBInfo:
        """Set database version"""
        info = self._get_info()

        if info:
            info.version = version
            return self.update(info)
        else:
            info = DBInfo(version=version, check_for_updates=True)
            return self.add(info)

    def get_update_check_enabled(self) -> bool:
        """Check if update checking is enabled"""
        info = self._get_info()
        return info.check_for_updates if info else True

    def set_update_check_enabled(self, enabled: bool) -> DBInfo:
        """Enable or disable update checking"""
        info = self._get_info()

        if info:
            info.check_for_updates = enabled
            return self.update(info)
        else:
            info = DBInfo(version=1, check_for_updates=enabled)
            return self.add(info)

    def get_last_write_timestamp(self) -> int | None:
        """Get last write timestamp"""
        info = self._get_info()
        return info.last_write_ts if info else None

    def update_last_write_timestamp(self, timestamp: int) -> DBInfo:
        """Update last write timestamp"""
        info = self._get_info()

        if info:
            info.last_write_ts = timestamp
            return self.update(info)
        else:
            info = DBInfo(
                version=1,
                check_for_updates=True,
                last_write_ts=timestamp,
            )
            return self.add(info)

    def get_last_data_migration(self) -> int | None:
        """Get last data migration version"""
        info = self._get_info()
        return info.last_data_migration if info else None

    def set_last_data_migration(self, migration_version: int) -> DBInfo:
        """Set last data migration version"""
        info = self._get_info()

        if info:
            info.last_data_migration = migration_version
            return self.update(info)
        else:
            info = DBInfo(
                version=1,
                check_for_updates=True,
                last_data_migration=migration_version,
            )
            return self.add(info)

    def get_last_owned_assets_update(self) -> int | None:
        """Get last owned assets update timestamp"""
        info = self._get_info()
        return info.last_owned_assets_update if info else None

    def set_last_owned_assets_update(self, timestamp: int) -> DBInfo:
        """Set last owned assets update timestamp"""
        info = self._get_info()

        if info:
            info.last_owned_assets_update = timestamp
            return self.update(info)
        else:
            info = DBInfo(
                version=1,
                check_for_updates=True,
                last_owned_assets_update=timestamp,
            )
            return self.add(info)

    def get_info(self) -> DBInfo | None:
        """Get full database info"""
        return self._get_info()

    def reset_info(self) -> DBInfo:
        """Reset database info to defaults"""
        # Delete existing info
        self.session.query(DBInfo).delete()
        self.session.flush()

        # Create new with defaults
        info = DBInfo(
            version=1,
            check_for_updates=True,
        )
        return self.add(info)

    def _get_info(self) -> DBInfo | None:
        """Internal method to get database info"""
        stmt = select(DBInfo).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def needs_migration(self, target_version: int) -> bool:
        """Check if database needs migration"""
        current_version = self.get_version()
        return current_version is None or current_version < target_version

    def needs_data_migration(self, target_migration: int) -> bool:
        """Check if database needs data migration"""
        last_migration = self.get_last_data_migration()
        return last_migration is None or last_migration < target_migration

    def update_info(
        self,
        version: int | None = None,
        check_for_updates: bool | None = None,
        last_write_ts: int | None = None,
        last_data_migration: int | None = None,
        last_owned_assets_update: int | None = None,
    ) -> DBInfo:
        """Update multiple info fields at once"""
        info = self._get_info()

        if not info:
            info = DBInfo(version=version or 1, check_for_updates=True)
            self.session.add(info)
        else:
            if version is not None:
                info.version = version
            if check_for_updates is not None:
                info.check_for_updates = check_for_updates
            if last_write_ts is not None:
                info.last_write_ts = last_write_ts
            if last_data_migration is not None:
                info.last_data_migration = last_data_migration
            if last_owned_assets_update is not None:
                info.last_owned_assets_update = last_owned_assets_update

        self.session.flush()
        return info
