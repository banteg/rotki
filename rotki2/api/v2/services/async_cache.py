"""Async Cache service for v2 API.

Handles business logic for cache operations.
"""
from typing import TYPE_CHECKING, Any

from rotki2.api.v2.repositories.cache import CacheRepository
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.types import ChecksumEvmAddress, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.types import NodeName
    from rotkehlchen.types import SupportedBlockchain


class AsyncCacheService:
    """Async service for cache operations."""
    
    def __init__(self, cache_repository: CacheRepository):
        self.cache_repository = cache_repository
    
    # General cache operations
    
    async def get_cache_value(
        self,
        key: DBCacheStatic | DBCacheDynamic | str,
        **kwargs: Any,
    ) -> Any:
        """Get a value from cache, handling both static and dynamic keys."""
        if isinstance(key, DBCacheStatic):
            return await self.cache_repository.get_value(key)
        elif isinstance(key, DBCacheDynamic):
            return await self.cache_repository.get_dynamic_cache_value(key, **kwargs)
        else:
            return await self.cache_repository.get_value(key)
    
    async def set_cache_value(
        self,
        key: DBCacheStatic | DBCacheDynamic | str,
        value: Any,
        **kwargs: Any,
    ) -> None:
        """Set a value in cache, handling both static and dynamic keys."""
        if isinstance(key, DBCacheStatic):
            await self.cache_repository.set_value(key, str(value))
        elif isinstance(key, DBCacheDynamic):
            await self.cache_repository.set_dynamic_cache_value(key, value, **kwargs)
        else:
            await self.cache_repository.set_value(key, str(value))
    
    async def delete_cache_value(
        self,
        key: DBCacheStatic | DBCacheDynamic | str,
        **kwargs: Any,
    ) -> None:
        """Delete a value from cache, handling both static and dynamic keys."""
        if isinstance(key, DBCacheStatic):
            await self.cache_repository.delete_value(key)
        elif isinstance(key, DBCacheDynamic):
            await self.cache_repository.delete_dynamic_cache_value(key, **kwargs)
        else:
            await self.cache_repository.delete_value(key)
    
    # Specific cache operations
    
    async def get_last_balance_save_time(self) -> Timestamp | None:
        """Get the last time balances were saved."""
        return await self.cache_repository.get_last_balance_save_time()
    
    async def update_last_balance_save_time(self, timestamp: Timestamp) -> None:
        """Update the last balance save time."""
        await self.cache_repository.set_last_balance_save_time(timestamp)
    
    async def get_last_data_upload_ts(self) -> Timestamp | None:
        """Get the last time data was uploaded."""
        return await self.cache_repository.get_last_data_upload_ts()
    
    async def update_last_data_upload_ts(self, timestamp: Timestamp) -> None:
        """Update the last data upload timestamp."""
        await self.cache_repository.set_last_data_upload_ts(timestamp)
    
    async def get_last_evm_accounts_detect_ts(self) -> Timestamp | None:
        """Get the last time EVM accounts were detected."""
        value = await self.cache_repository.get_value(DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS)
        return Timestamp(int(value)) if value else None
    
    async def update_last_evm_accounts_detect_ts(self, timestamp: Timestamp) -> None:
        """Update the last EVM accounts detection timestamp."""
        await self.cache_repository.set_value(
            DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS,
            str(timestamp),
        )
    
    # Exchange-specific operations
    
    async def get_last_query_ts(
        self,
        location: str,
        location_name: str,
        account_id: str,
    ) -> Timestamp | None:
        """Get the last query timestamp for an exchange account."""
        return await self.cache_repository.get_dynamic_cache_value(
            DBCacheDynamic.LAST_QUERY_TS,
            location=location,
            location_name=location_name,
            account_id=account_id,
        )
    
    async def update_last_query_ts(
        self,
        location: str,
        location_name: str,
        account_id: str,
        timestamp: Timestamp,
    ) -> None:
        """Update the last query timestamp for an exchange account."""
        await self.cache_repository.set_dynamic_cache_value(
            DBCacheDynamic.LAST_QUERY_TS,
            timestamp,
            location=location,
            location_name=location_name,
            account_id=account_id,
        )
    
    async def get_last_query_id(
        self,
        location: str,
        location_name: str,
        account_id: str,
    ) -> str | None:
        """Get the last query ID for an exchange account."""
        return await self.cache_repository.get_dynamic_cache_value(
            DBCacheDynamic.LAST_QUERY_ID,
            location=location,
            location_name=location_name,
            account_id=account_id,
        )
    
    async def update_last_query_id(
        self,
        location: str,
        location_name: str,
        account_id: str,
        query_id: str,
    ) -> None:
        """Update the last query ID for an exchange account."""
        await self.cache_repository.set_dynamic_cache_value(
            DBCacheDynamic.LAST_QUERY_ID,
            query_id,
            location=location,
            location_name=location_name,
            account_id=account_id,
        )
    
    # Ethereum-specific operations
    
    async def get_withdrawals_cache(
        self,
        address: ChecksumEvmAddress,
    ) -> tuple[Timestamp | None, int | None]:
        """Get ETH withdrawals cache data for an address.
        
        Returns (timestamp, index) or (None, None) if not cached.
        """
        ts = await self.cache_repository.get_dynamic_cache_value(
            DBCacheDynamic.WITHDRAWALS_TS,
            address=address,
        )
        idx = await self.cache_repository.get_dynamic_cache_value(
            DBCacheDynamic.WITHDRAWALS_IDX,
            address=address,
        )
        return ts, idx
    
    async def update_withdrawals_cache(
        self,
        address: ChecksumEvmAddress,
        timestamp: Timestamp,
        index: int,
    ) -> None:
        """Update ETH withdrawals cache data for an address."""
        await self.cache_repository.set_dynamic_cache_value(
            DBCacheDynamic.WITHDRAWALS_TS,
            timestamp,
            address=address,
        )
        await self.cache_repository.set_dynamic_cache_value(
            DBCacheDynamic.WITHDRAWALS_IDX,
            index,
            address=address,
        )
    
    # Query range operations
    
    async def get_query_range(self, name: str) -> tuple[Timestamp | None, Timestamp | None]:
        """Get the used query range for a given name."""
        return await self.cache_repository.get_used_query_range(name)
    
    async def update_query_range(
        self,
        name: str,
        start_ts: Timestamp | None,
        end_ts: Timestamp | None,
    ) -> None:
        """Update the used query range for a given name."""
        await self.cache_repository.update_used_query_range(name, start_ts, end_ts)
    
    async def delete_query_range(self, name: str) -> None:
        """Delete a query range entry."""
        await self.cache_repository.delete_used_query_range(name)
    
    # Utility operations
    
    async def clear_all_caches(self) -> None:
        """Clear all cache entries."""
        await self.cache_repository.clear_cache()
    
    async def is_cache_empty(self) -> bool:
        """Check if the cache is empty."""
        # Check if last balance save exists as a proxy for whether cache has data
        value = await self.cache_repository.get_value(DBCacheStatic.LAST_BALANCE_SAVE)
        return value is None