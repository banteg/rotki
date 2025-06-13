"""Async Cache repository for v2 API.

Handles all cache-related async database operations.
"""
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotki2.db.models.user.cache import KeyValueCache, UsedQueryRange
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from collections.abc import Callable


class AsyncCacheRepository:
    """Async repository for cache operations.
    
    Note: This doesn't inherit from AsyncBaseRepository as it manages
    multiple tables (key_value_cache and used_query_ranges).
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Key-Value Cache Operations
    
    async def get_value(
        self,
        key: DBCacheStatic | str,
    ) -> str | None:
        """Get a value from the key-value cache."""
        key_str = key.value if isinstance(key, DBCacheStatic) else key
        
        statement = select(KeyValueCache).where(KeyValueCache.name == key_str)
        result = await self.session.execute(statement)
        cache_entry = result.scalar_one_or_none()
        
        return cache_entry.value if cache_entry else None
    
    async def get_dynamic_cache_value(
        self,
        key: DBCacheDynamic,
        **kwargs: Any,
    ) -> Any:
        """Get a value from the key-value cache for dynamic keys.
        
        Returns the deserialized value or None if not found.
        """
        db_key = key.get_db_key(**kwargs)
        value = await self.get_value(db_key)
        
        if value is None:
            return None
        
        # Deserialize using the key's callback
        return key.deserialize_callback(value)
    
    async def set_value(
        self,
        key: DBCacheStatic | str,
        value: str,
    ) -> None:
        """Set a value in the key-value cache."""
        key_str = key.value if isinstance(key, DBCacheStatic) else key
        
        # Check if entry exists
        statement = select(KeyValueCache).where(KeyValueCache.name == key_str)
        result = await self.session.execute(statement)
        cache_entry = result.scalar_one_or_none()
        
        if cache_entry:
            # Update existing
            cache_entry.value = value
            self.session.add(cache_entry)
        else:
            # Create new
            new_entry = KeyValueCache(name=key_str, value=value)
            self.session.add(new_entry)
        
        await self.session.commit()
    
    async def set_dynamic_cache_value(
        self,
        key: DBCacheDynamic,
        value: Any,
        **kwargs: Any,
    ) -> None:
        """Set a value in the key-value cache for dynamic keys."""
        db_key = key.get_db_key(**kwargs)
        # Convert value to string for storage
        str_value = str(value)
        await self.set_value(db_key, str_value)
    
    async def delete_value(
        self,
        key: DBCacheStatic | str,
    ) -> None:
        """Delete a value from the key-value cache."""
        key_str = key.value if isinstance(key, DBCacheStatic) else key
        
        statement = select(KeyValueCache).where(KeyValueCache.name == key_str)
        result = await self.session.execute(statement)
        cache_entry = result.scalar_one_or_none()
        
        if cache_entry:
            await self.session.delete(cache_entry)
            await self.session.commit()
    
    async def delete_dynamic_cache_value(
        self,
        key: DBCacheDynamic,
        **kwargs: Any,
    ) -> None:
        """Delete a value from the key-value cache for dynamic keys."""
        db_key = key.get_db_key(**kwargs)
        await self.delete_value(db_key)
    
    # Query Range Operations
    
    async def get_used_query_range(self, name: str) -> tuple[Timestamp | None, Timestamp | None]:
        """Get the used query range for a given name.
        
        Returns (start_ts, end_ts) or (None, None) if not found.
        """
        statement = select(UsedQueryRange).where(UsedQueryRange.name == name)
        result = await self.session.execute(statement)
        query_range = result.scalar_one_or_none()
        
        if query_range:
            start_ts = Timestamp(query_range.start_ts) if query_range.start_ts else None
            end_ts = Timestamp(query_range.end_ts) if query_range.end_ts else None
            return start_ts, end_ts
        
        return None, None
    
    async def update_used_query_range(
        self,
        name: str,
        start_ts: Timestamp | None,
        end_ts: Timestamp | None,
    ) -> None:
        """Update the used query range for a given name."""
        # Check if entry exists
        statement = select(UsedQueryRange).where(UsedQueryRange.name == name)
        result = await self.session.execute(statement)
        query_range = result.scalar_one_or_none()
        
        if query_range:
            # Update existing
            query_range.start_ts = int(start_ts) if start_ts else None
            query_range.end_ts = int(end_ts) if end_ts else None
            self.session.add(query_range)
        else:
            # Create new
            new_range = UsedQueryRange(
                name=name,
                start_ts=int(start_ts) if start_ts else None,
                end_ts=int(end_ts) if end_ts else None,
            )
            self.session.add(new_range)
        
        await self.session.commit()
    
    async def delete_used_query_range(self, name: str) -> None:
        """Delete a used query range entry."""
        statement = select(UsedQueryRange).where(UsedQueryRange.name == name)
        result = await self.session.execute(statement)
        query_range = result.scalar_one_or_none()
        
        if query_range:
            await self.session.delete(query_range)
            await self.session.commit()
    
    async def get_last_balance_save_time(self) -> Timestamp | None:
        """Get the timestamp of the last balance save."""
        value = await self.get_value(DBCacheStatic.LAST_BALANCE_SAVE)
        return Timestamp(int(value)) if value else None
    
    async def set_last_balance_save_time(self, timestamp: Timestamp) -> None:
        """Set the timestamp of the last balance save."""
        await self.set_value(DBCacheStatic.LAST_BALANCE_SAVE, str(timestamp))
    
    async def get_last_data_upload_ts(self) -> Timestamp | None:
        """Get the timestamp of the last data upload."""
        value = await self.get_value(DBCacheStatic.LAST_DATA_UPLOAD_TS)
        return Timestamp(int(value)) if value else None
    
    async def set_last_data_upload_ts(self, timestamp: Timestamp) -> None:
        """Set the timestamp of the last data upload."""
        await self.set_value(DBCacheStatic.LAST_DATA_UPLOAD_TS, str(timestamp))
    
    async def get_last_owned_assets_update(self) -> Timestamp | None:
        """Get the timestamp of the last owned assets update."""
        value = await self.get_value(DBCacheStatic.LAST_OWNED_ASSETS_UPDATE)
        return Timestamp(int(value)) if value else None
    
    async def set_last_owned_assets_update(self, timestamp: Timestamp) -> None:
        """Set the timestamp of the last owned assets update."""
        await self.set_value(DBCacheStatic.LAST_OWNED_ASSETS_UPDATE, str(timestamp))
    
    async def clear_cache(self) -> None:
        """Clear all cache entries."""
        # Clear key-value cache
        statement = select(KeyValueCache)
        result = await self.session.execute(statement)
        for entry in result.scalars().all():
            await self.session.delete(entry)
        
        # Clear query ranges
        statement = select(UsedQueryRange)
        result = await self.session.execute(statement)
        for entry in result.scalars().all():
            await self.session.delete(entry)
        
        await self.session.commit()