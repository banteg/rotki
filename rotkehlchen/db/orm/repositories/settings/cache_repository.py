"""Repository for cache management"""

from typing import Any, Optional, Union, overload

from sqlalchemy import delete, select

from rotkehlchen.db.orm.models import KeyValueCache
from rotkehlchen.db.orm.repositories.base import BaseRepository


class CacheRepository(BaseRepository[KeyValueCache]):
    """Repository for managing key-value cache"""
    
    def __init__(self, session):
        super().__init__(session, KeyValueCache)
    
    @overload
    def get_cache(self, name: str) -> Optional[str]: ...
    
    @overload
    def get_cache(self, name: str, default: str) -> str: ...
    
    def get_cache(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get cached value by name"""
        cache_entry = self.get(name=name)
        if cache_entry and cache_entry.value is not None:
            return cache_entry.value
        return default
    
    def set_cache(self, name: str, value: Union[str, int, float, bool]) -> None:
        """Set cache value"""
        str_value = str(value)
        
        cache_entry = self.get(name=name)
        if cache_entry:
            cache_entry.value = str_value
            self.update(cache_entry)
        else:
            self.add(KeyValueCache(name=name, value=str_value))
    
    def delete_cache(self, name: str) -> bool:
        """Delete cache entry"""
        return self.delete_by(name=name) > 0
    
    def delete_cache_by_prefix(self, prefix: str) -> int:
        """Delete all cache entries with names starting with prefix"""
        stmt = delete(KeyValueCache).where(
            KeyValueCache.name.like(f'{prefix}%')
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def get_cache_by_prefix(self, prefix: str) -> dict[str, str]:
        """Get all cache entries with names starting with prefix"""
        stmt = select(KeyValueCache).where(
            KeyValueCache.name.like(f'{prefix}%')
        )
        entries = self.session.execute(stmt).scalars().all()
        return {entry.name: entry.value for entry in entries if entry.value is not None}
    
    def clear_all_cache(self) -> int:
        """Clear all cache entries"""
        stmt = delete(KeyValueCache)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def update_multiple(self, cache_dict: dict[str, Any]) -> None:
        """Update multiple cache entries at once"""
        for name, value in cache_dict.items():
            self.set_cache(name, value)
    
    def exists_cache(self, name: str) -> bool:
        """Check if cache entry exists"""
        return self.exists(name=name)