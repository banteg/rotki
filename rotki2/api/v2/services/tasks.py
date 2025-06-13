"""Task management service for rotki2."""
import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotki2.tasks.async_manager import AsyncTaskManager, DEFAULT_MAX_TASKS_NUM
from rotki2.tasks.anyio_manager import AnyioTaskManager

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.updates import RotkiDataUpdater
    from rotkehlchen.exchanges.manager import ExchangeManager
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.premium.sync import PremiumSyncManager
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncTaskService:
    """Service for managing async background tasks."""

    def __init__(
        self,
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
        cryptocompare: 'Cryptocompare',
        chains_aggregator: 'ChainsAggregator',
        exchange_manager: 'ExchangeManager',
        data_updater: 'RotkiDataUpdater',
        username: str,
        max_tasks_num: int = DEFAULT_MAX_TASKS_NUM,
        premium_sync_manager: 'PremiumSyncManager | None' = None,
    ) -> None:
        """Initialize the task service."""
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.cryptocompare = cryptocompare
        self.chains_aggregator = chains_aggregator
        self.exchange_manager = exchange_manager
        self.data_updater = data_updater
        self.username = username
        self.max_tasks_num = max_tasks_num
        self.premium_sync_manager = premium_sync_manager

        self.anyio_manager: AnyioTaskManager | None = None
        self.task_manager: AsyncTaskManager | None = None
        self._is_premium = False

    async def start(self) -> None:
        """Start the task management system."""
        if self.anyio_manager is not None:
            log.warning('Task service already started')
            return

        log.info('Starting async task management system')
        
        # Create the anyio task manager
        self.anyio_manager = AnyioTaskManager(self.msg_aggregator)
        
        # Enter async context
        await self.anyio_manager.__aenter__()
        
        # Create the main task manager
        self.task_manager = AsyncTaskManager(
            max_tasks_num=self.max_tasks_num,
            task_manager=self.anyio_manager,
            api_task_count=0,  # Will be updated by API layer
            database=self.database,
            cryptocompare=self.cryptocompare,
            premium_sync_manager=self.premium_sync_manager,
            chains_aggregator=self.chains_aggregator,
            exchange_manager=self.exchange_manager,
            deactivate_premium=self._deactivate_premium,
            activate_premium=self._activate_premium,
            query_balances=self._query_balances_placeholder,
            msg_aggregator=self.msg_aggregator,
            data_updater=self.data_updater,
            username=self.username,
        )

    async def stop(self) -> None:
        """Stop the task management system."""
        if self.task_manager:
            await self.task_manager.stop_scheduling()
            self.task_manager = None

        if self.anyio_manager:
            await self.anyio_manager.__aexit__(None, None, None)
            self.anyio_manager = None

        log.info('Stopped async task management system')

    async def enable_scheduling(self) -> None:
        """Enable task scheduling (called after user login)."""
        if not self.task_manager:
            raise RuntimeError('Task manager not started')
        
        log.info('Enabling task scheduling')
        self.task_manager.should_schedule = True
        await self.task_manager.start_scheduling()

    async def disable_scheduling(self) -> None:
        """Disable task scheduling (called during logout)."""
        if self.task_manager:
            log.info('Disabling task scheduling')
            await self.task_manager.stop_scheduling()

    async def get_task_status(self) -> dict:
        """Get current task status."""
        if not self.anyio_manager or not self.task_manager:
            return {'status': 'stopped', 'active_tasks': 0, 'total_tasks': 0}

        active_tasks = [task for task in self.anyio_manager.tasks if not task.is_complete]
        return {
            'status': 'running' if self.task_manager.should_schedule else 'paused',
            'active_tasks': len(active_tasks),
            'total_tasks': len(self.anyio_manager.tasks),
            'max_tasks': self.task_manager.max_tasks_num,
            'tasks': [
                {
                    'name': task.name,
                    'is_complete': task.is_complete,
                    'has_error': task.exception is not None,
                    'error': str(task.exception) if task.exception else None,
                }
                for task in self.anyio_manager.tasks[-10:]  # Last 10 tasks
            ],
        }

    def update_api_task_count(self, count: int) -> None:
        """Update the count of API tasks for scheduling calculations."""
        if self.task_manager:
            self.task_manager.api_task_count = count

    def _deactivate_premium(self) -> None:
        """Deactivate premium status."""
        self._is_premium = False
        log.info('Premium status deactivated')

    def _activate_premium(self, premium: 'Premium') -> None:
        """Activate premium status."""
        self._is_premium = True
        log.info('Premium status activated')

    async def _query_balances_placeholder(self, **kwargs) -> None:
        """Placeholder for balance querying - should be replaced with actual service."""
        log.warning('Balance querying not yet implemented in async task system')

    async def force_task_execution(self, task_name: str) -> bool:
        """Force execution of a specific task type."""
        if not self.task_manager:
            return False

        # Map task names to their methods
        task_mapping = {
            'cryptocompare': self.task_manager._maybe_schedule_cryptocompare_query,
            'evm_transactions': self.task_manager._maybe_query_evm_transactions,
            'events_processing': self.task_manager._maybe_run_events_processing,
            'premium_status': self.task_manager._maybe_check_premium_status,
            'balance_snapshot': self.task_manager._maybe_update_snapshot_balances,
        }

        task_method = task_mapping.get(task_name)
        if task_method:
            return await task_method()
        
        log.warning(f'Unknown task name: {task_name}')
        return False

    async def __aenter__(self) -> 'AsyncTaskService':
        """Enter async context."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        await self.stop()