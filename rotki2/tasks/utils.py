"""Utility functions for async task management."""
import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


async def should_run_periodic_task_async(
        database: 'DBHandler',
        key_name: Literal[
            DBCacheStatic.LAST_DATA_UPDATES_TS,
            DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS,
            DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY,
            DBCacheStatic.LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY,
            DBCacheStatic.LAST_OWNED_ASSETS_UPDATE,
            DBCacheStatic.LAST_MONERIUM_QUERY_TS,
            DBCacheStatic.LAST_AAVE_V3_ASSETS_UPDATE,
            DBCacheStatic.LAST_DELETE_PAST_CALENDAR_EVENTS,
            DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
            DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS,
            DBCacheStatic.LAST_GNOSISPAY_QUERY_TS,
            DBCacheStatic.LAST_SPARK_ASSETS_UPDATE,
        ],
        refresh_period: int,
) -> bool:
    """
    Async version of should_run_periodic_task.
    
    Checks if enough time has elapsed since the last run of a periodic task in order to run
    it again.
    """
    with database.conn.read_ctx() as cursor:
        cursor.execute('SELECT value FROM key_value_cache WHERE name=?', (key_name.value,))
        timestamp_in_db = cursor.fetchone()

    if timestamp_in_db is None:
        return True

    last_update_ts = deserialize_timestamp(timestamp_in_db[0])
    return ts_now() - last_update_ts >= refresh_period


class TaskSchedulingMixin:
    """Mixin class providing common task scheduling utilities."""
    
    def __init__(self) -> None:
        """Initialize the mixin."""
        # Track task frequency to prevent over-scheduling
        self.task_frequencies: dict[str, int] = {}
    
    def can_schedule_task(self, task_name: str, frequency_seconds: int) -> bool:
        """Check if a task can be scheduled based on its frequency."""
        now = ts_now()
        last_run = self.task_frequencies.get(task_name, 0)
        
        if now - last_run >= frequency_seconds:
            self.task_frequencies[task_name] = now
            return True
        return False
    
    def reset_task_frequency(self, task_name: str) -> None:
        """Reset the frequency counter for a task."""
        self.task_frequencies.pop(task_name, None)


class TaskResultStorage:
    """Helper class for storing and retrieving task results."""
    
    def __init__(self, database: 'DBHandler'):
        self.database = database
    
    async def store_task_completion(self, task_name: str, cache_key: DBCacheStatic) -> None:
        """Store task completion timestamp."""
        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=cache_key,
                value=ts_now(),
            )
    
    async def get_last_task_run(self, cache_key: DBCacheStatic) -> int | None:
        """Get the last time a task was run."""
        with self.database.conn.read_ctx() as cursor:
            result = self.database.get_static_cache(cursor=cursor, name=cache_key)
        return result