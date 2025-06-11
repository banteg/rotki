"""Repository for ABI cache management"""

import time

from sqlalchemy import delete, func, select

from rotkehlchen.db.orm.models import EvmAbiCache
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import ChecksumEvmAddress, Timestamp


class ABICacheRepository(BaseRepository[EvmAbiCache]):
    """Repository for managing EVM ABI cache"""

    def __init__(self, session):
        super().__init__(session, EvmAbiCache)

    def add_abi(
        self,
        address: ChecksumEvmAddress,
        abi: str,
        last_queried_timestamp: Timestamp,
    ) -> EvmAbiCache:
        """Add or update ABI cache entry"""
        # Check if entry exists
        existing = self.get_abi(address)

        if existing:
            existing.abi = abi
            existing.last_queried_timestamp = int(last_queried_timestamp)
            return self.update(existing)
        else:
            cache_entry = EvmAbiCache(
                address=address,
                abi=abi,
                last_queried_timestamp=int(last_queried_timestamp),
            )
            return self.add(cache_entry)

    def get_abi(self, address: ChecksumEvmAddress) -> EvmAbiCache | None:
        """Get ABI for address"""
        return self.get(address=address)

    def get_abi_string(self, address: ChecksumEvmAddress) -> str | None:
        """Get ABI string for address"""
        entry = self.get_abi(address)
        return entry.abi if entry else None

    def delete_abi(self, address: ChecksumEvmAddress) -> bool:
        """Delete ABI cache entry"""
        return self.delete_by(address=address) > 0

    def abi_exists(self, address: ChecksumEvmAddress) -> bool:
        """Check if ABI exists for address"""
        return self.get_abi(address) is not None

    def get_all_cached_addresses(self) -> list[ChecksumEvmAddress]:
        """Get all addresses with cached ABIs"""
        stmt = select(EvmAbiCache.address)
        return list(self.session.execute(stmt).scalars().all())

    def get_cache_count(self) -> int:
        """Get total count of cached ABIs"""
        query = select(func.count()).select_from(EvmAbiCache)
        return self.session.execute(query).scalar() or 0

    def delete_old_entries(self, older_than: Timestamp) -> int:
        """Delete cache entries older than timestamp"""
        stmt = delete(EvmAbiCache).filter(
            EvmAbiCache.last_queried_timestamp < int(older_than),
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def get_entries_by_age(
        self,
        newer_than: Timestamp | None = None,
        older_than: Timestamp | None = None,
    ) -> list[EvmAbiCache]:
        """Get cache entries by age"""
        query = select(EvmAbiCache)

        if newer_than is not None:
            query = query.filter(
                EvmAbiCache.last_queried_timestamp > int(newer_than),
            )

        if older_than is not None:
            query = query.filter(
                EvmAbiCache.last_queried_timestamp < int(older_than),
            )

        return list(self.session.execute(query).scalars().all())

    def needs_refresh(
        self,
        address: ChecksumEvmAddress,
        max_age_seconds: int = 86400 * 30,  # 30 days default
    ) -> bool:
        """Check if ABI needs refresh based on age"""
        entry = self.get_abi(address)
        if not entry:
            return True

        current_ts = Timestamp(int(time.time()))
        age = current_ts - Timestamp(entry.last_queried_timestamp)

        return age > max_age_seconds

    def update_timestamp(
        self,
        address: ChecksumEvmAddress,
        timestamp: Timestamp,
    ) -> EvmAbiCache | None:
        """Update only the timestamp for a cache entry"""
        entry = self.get_abi(address)
        if not entry:
            return None

        entry.last_queried_timestamp = int(timestamp)
        return self.update(entry)

    def bulk_add_abis(
        self,
        abis_data: list[dict[str, any]],
    ) -> list[EvmAbiCache]:
        """Bulk add multiple ABIs"""
        entries = []

        for data in abis_data:
            # Check if exists
            existing = self.get_abi(data['address'])

            if existing:
                existing.abi = data['abi']
                existing.last_queried_timestamp = int(data['last_queried_timestamp'])
                entries.append(existing)
            else:
                entry = EvmAbiCache(
                    address=data['address'],
                    abi=data['abi'],
                    last_queried_timestamp=int(data['last_queried_timestamp']),
                )
                self.session.add(entry)
                entries.append(entry)

        self.session.flush()
        return entries

    def clear_cache(self) -> int:
        """Clear all ABI cache entries"""
        count = self.session.query(EvmAbiCache).delete()
        self.session.flush()
        return count
