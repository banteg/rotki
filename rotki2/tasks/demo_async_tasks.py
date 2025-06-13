"""Demo script showing the AsyncTaskManager in action."""
import asyncio
import logging
from typing import Any

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotki2.tasks.anyio_manager import AnyioTaskManager
from rotki2.tasks.async_manager import AsyncTaskManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self._cache = {}
        
    def conn(self):
        return self
        
    def read_ctx(self):
        return self
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass


class MockMessagesAggregator:
    """Mock message aggregator."""
    
    def add_error(self, message: str) -> None:
        log.error(f"User message: {message}")


class MockChainsAggregator:
    """Mock chains aggregator."""
    pass


class MockExchangeManager:
    """Mock exchange manager."""
    
    @property
    def connected_exchanges(self):
        return []


class MockDataUpdater:
    """Mock data updater."""
    pass


class MockCryptcompare:
    """Mock cryptocompare API."""
    
    def __init__(self):
        self.last_histohour_query_ts = 0


async def demo_async_task_simple():
    """Simple async task for demonstration."""
    log.info("Starting simple async task")
    await asyncio.sleep(2)  # Simulate work
    log.info("Simple async task completed")
    return "Task completed successfully"


async def demo_async_task_with_error():
    """Async task that raises an error for demonstration."""
    log.info("Starting async task that will fail")
    await asyncio.sleep(1)
    raise ValueError("This is a demo error")


async def demo_task_manager():
    """Demonstrate the async task manager."""
    log.info("Starting AsyncTaskManager demo")
    
    # Create mock dependencies
    database = MockDatabase()
    msg_aggregator = MockMessagesAggregator()
    cryptocompare = MockCryptcompare()
    chains_aggregator = MockChainsAggregator()
    exchange_manager = MockExchangeManager()
    data_updater = MockDataUpdater()
    
    # Create the anyio task manager
    async with AnyioTaskManager(msg_aggregator) as anyio_manager:
        # Create the async task manager
        task_manager = AsyncTaskManager(
            max_tasks_num=3,
            task_manager=anyio_manager,
            api_task_count=0,
            database=database,
            cryptocompare=cryptocompare,
            premium_sync_manager=None,
            chains_aggregator=chains_aggregator,
            exchange_manager=exchange_manager,
            deactivate_premium=lambda: None,
            activate_premium=lambda p: None,
            query_balances=lambda **kwargs: None,
            msg_aggregator=msg_aggregator,
            data_updater=data_updater,
            username="demo_user",
        )
        
        log.info("Task manager created")
        
        # Spawn some test tasks
        log.info("Spawning test tasks")
        
        # Task 1: Simple successful task
        task1 = await anyio_manager.spawn_and_track(
            after_seconds=None,
            task_name="Demo simple task",
            exception_is_error=True,
            method=demo_async_task_simple,
        )
        
        # Task 2: Task that will fail
        task2 = await anyio_manager.spawn_and_track(
            after_seconds=None,
            task_name="Demo error task",
            exception_is_error=True,
            method=demo_async_task_with_error,
        )
        
        # Task 3: Delayed task
        task3 = await anyio_manager.spawn_and_track(
            after_seconds=1.0,
            task_name="Demo delayed task",
            exception_is_error=True,
            method=demo_async_task_simple,
        )
        
        log.info(f"Spawned {len(anyio_manager.tasks)} tasks")
        
        # Monitor task completion
        for i in range(10):  # Wait up to 10 seconds
            await asyncio.sleep(1)
            
            completed_count = sum(1 for task in anyio_manager.tasks if task.is_complete)
            log.info(f"Iteration {i+1}: {completed_count}/{len(anyio_manager.tasks)} tasks completed")
            
            # Show task status
            for j, task in enumerate(anyio_manager.tasks):
                status = "COMPLETE" if task.is_complete else "RUNNING"
                error_info = f" (ERROR: {task.exception})" if task.exception else ""
                log.info(f"  Task {j+1}: {task.name} - {status}{error_info}")
            
            if completed_count == len(anyio_manager.tasks):
                break
        
        # Final status
        log.info("Final task status:")
        for i, task in enumerate(anyio_manager.tasks):
            result_info = f" -> {task.result}" if task.result and not task.exception else ""
            error_info = f" (ERROR: {task.exception})" if task.exception else ""
            log.info(f"  Task {i+1}: {task.name}{result_info}{error_info}")
        
        log.info("Demo completed")


async def demo_periodic_scheduling():
    """Demonstrate periodic task scheduling."""
    log.info("Starting periodic scheduling demo")
    
    # This would show how the actual scheduling works
    # For now, just a placeholder
    log.info("Periodic scheduling demo - would show actual task scheduling here")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def main():
        await demo_task_manager()
        # await demo_periodic_scheduling()
    
    asyncio.run(main())