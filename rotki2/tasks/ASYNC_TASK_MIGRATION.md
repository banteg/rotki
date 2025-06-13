# Async Task Manager Migration Guide

This document describes the migration from the gevent-based `TaskManager` to the new async `AsyncTaskManager` using anyio.

## Overview

The original `TaskManager` in rotkehlchen uses gevent greenlets for concurrency. The new `AsyncTaskManager` replaces this with modern Python async/await using anyio task groups, providing:

- Better integration with async codebases
- More predictable concurrency behavior
- Improved error handling and task lifecycle management
- Platform-independent async operations

## Architecture

### Original (Gevent-based)
```
TaskManager
├── GreenletManager (tracks individual greenlets)
├── potential_tasks (list of scheduling functions)
├── running_greenlets (dict mapping functions to greenlets)
└── schedule_lock (gevent.lock.Semaphore)
```

### New (Anyio-based)
```
AsyncTaskManager
├── AnyioTaskManager (tracks individual async tasks)
├── potential_tasks (list of async scheduling functions)
├── running_tasks (dict mapping functions to task names)
└── schedule_lock (anyio.Lock)
```

## Key Changes

### 1. Task Spawning
**Before:**
```python
greenlet = self.greenlet_manager.spawn_and_track(
    after_seconds=None,
    task_name='Query ETH transactions',
    exception_is_error=True,
    method=evm_manager.transactions.single_address_query_transactions,
    address=address,
    start_ts=0,
    end_ts=now,
)
```

**After:**
```python
task = await self.task_manager.spawn_and_track(
    after_seconds=None,
    task_name='Query ETH transactions',
    exception_is_error=True,
    method=evm_manager.transactions.single_address_query_transactions,
    address=address,
    start_ts=0,
    end_ts=now,
)
```

### 2. Scheduling Loop
**Before (gevent):**
```python
def schedule(self) -> None:
    with self.schedule_lock:
        self._schedule()  # Synchronous scheduling
```

**After (async):**
```python
async def schedule(self) -> None:
    async with self.schedule_lock:
        await self._schedule()  # Asynchronous scheduling
```

### 3. Task State Management
**Before:**
- Tasks are gevent.Greenlet objects
- State tracked via `greenlet.dead` property
- Results accessed via `greenlet.value` or `greenlet.exception`

**After:**
- Tasks are `AsyncTask` objects with explicit state
- State tracked via `task.is_complete` and `task.exception`
- Results stored in `task.result`

## Task Types and Migration Status

### ✅ Fully Implemented
1. **Cryptocompare Query** - Historical price data fetching
2. **Premium Status Check** - Premium subscription validation
3. **Events Processing** - Process and combine historical events
4. **DB Upload** - Premium database sync

### 🚧 Partially Implemented
1. **EVM Transactions Query** - Basic structure complete, needs async conversion of underlying methods
2. **Balance Snapshots** - Framework in place, needs async balance service integration

### ⏳ Pending Implementation
1. **XPUB Derivation** - Bitcoin address derivation
2. **Exchange History** - Trading history queries
3. **EVM Transaction Receipts** - Transaction receipt fetching
4. **EVM Transaction Decoding** - Transaction event decoding
5. **Data Updates** - External data source updates
6. **Protocol Cache Updates** (Yearn, Morpho, Aura, Pendle, etc.)
7. **Account Detection** - Auto-detect new accounts
8. **Spam Token Detection** - Identify and mark spam tokens
9. **Calendar Tasks** - Reminder creation and notifications
10. **Blockchain-specific Tasks** (ETH2 blocks, withdrawals, Graph delegation)

## Implementation Patterns

### Async Task Method Pattern
```python
async def _maybe_schedule_task_name(self) -> bool:
    """Schedule task if conditions are met."""
    # 1. Check if task should run (timing, prerequisites)
    if not should_run_condition():
        return False
    
    # 2. Check if task is already running
    if self.task_manager.has_task('Task Name'):
        return False
    
    # 3. Prepare task parameters
    task_name = 'Descriptive Task Name'
    
    # 4. Schedule the task
    await self.task_manager.spawn_and_track(
        after_seconds=None,  # or delay in seconds
        task_name=task_name,
        exception_is_error=True,  # whether exceptions are errors
        method=self._actual_task_method,  # async method to run
        **task_params,  # task parameters
    )
    return True

async def _actual_task_method(self, **params) -> Any:
    """The actual async task implementation."""
    # Task logic here - must be async
    result = await some_async_operation()
    
    # Update completion timestamp if needed
    with self.database.user_write() as write_cursor:
        self.database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_TASK_TS,
            value=ts_now(),
        )
    
    return result
```

### Service Integration Pattern
```python
class AsyncTaskService:
    """Service wrapper for task management."""
    
    async def start(self) -> None:
        """Initialize task system."""
        self.anyio_manager = AnyioTaskManager(self.msg_aggregator)
        await self.anyio_manager.__aenter__()
        
        self.task_manager = AsyncTaskManager(...)
    
    async def enable_scheduling(self) -> None:
        """Start periodic task scheduling."""
        self.task_manager.should_schedule = True
        await self.task_manager.start_scheduling()
    
    async def stop(self) -> None:
        """Cleanup task system."""
        if self.task_manager:
            await self.task_manager.stop_scheduling()
        if self.anyio_manager:
            await self.anyio_manager.__aexit__(None, None, None)
```

## Migration Checklist

### Phase 1: Foundation ✅
- [x] Create `AnyioTaskManager` base class
- [x] Create `AsyncTaskManager` main class
- [x] Implement task scheduling framework
- [x] Create `AsyncTaskService` wrapper
- [x] Set up basic task lifecycle management

### Phase 2: Core Tasks (In Progress)
- [x] Migrate cryptocompare price queries
- [x] Migrate premium status checking
- [x] Migrate events processing
- [x] Migrate EVM transaction querying (structure)
- [ ] Complete EVM transaction method async conversion
- [ ] Migrate balance snapshot updates
- [ ] Migrate exchange history queries

### Phase 3: Blockchain Tasks
- [ ] Migrate XPUB derivation
- [ ] Migrate EVM transaction receipts
- [ ] Migrate EVM transaction decoding
- [ ] Migrate ETH2 validator tasks
- [ ] Migrate withdrawal processing

### Phase 4: Protocol Tasks
- [ ] Migrate DeFi protocol cache updates
- [ ] Migrate spam token detection
- [ ] Migrate account detection
- [ ] Migrate calendar tasks

### Phase 5: Integration & Testing
- [ ] Update dependency injection
- [ ] Create comprehensive tests
- [ ] Performance benchmarking
- [ ] Migration validation

## Error Handling

The async task manager provides improved error handling:

```python
async def _handle_task_exception(self, task: AsyncTask) -> None:
    """Handle task exceptions with proper async context."""
    if isinstance(task.exception, asyncio.CancelledError):
        log.debug(f'Task {task.name} was cancelled')
        return
    
    # Log detailed error information
    if task.exception_is_error:
        log.error(f'{task.name} failed: {task.exception}')
        self.msg_aggregator.add_error(f'{task.name} failed')
```

## Testing

### Unit Tests
Test individual task scheduling methods:
```python
async def test_cryptocompare_scheduling():
    task_manager = create_test_task_manager()
    
    # Test conditions for scheduling
    assert await task_manager._maybe_schedule_cryptocompare_query()
    
    # Verify task was created
    assert task_manager.task_manager.has_task('Cryptocompare')
```

### Integration Tests
Test complete task lifecycle:
```python
async def test_task_lifecycle():
    async with AsyncTaskService(...) as service:
        await service.enable_scheduling()
        
        # Wait for tasks to complete
        await asyncio.sleep(5)
        
        # Verify results
        status = await service.get_task_status()
        assert status['active_tasks'] >= 0
```

## Performance Considerations

1. **Task Concurrency**: Maintain `max_tasks_num` limit to prevent resource exhaustion
2. **Scheduling Frequency**: Run scheduler every 60 seconds (configurable)
3. **Task Prioritization**: Use random shuffle for fair task distribution
4. **Resource Cleanup**: Automatically clean up completed tasks

## Future Enhancements

1. **Task Priorities**: Add priority levels for task scheduling
2. **Task Dependencies**: Support task dependency chains
3. **Progress Tracking**: Detailed progress reporting for long-running tasks
4. **Task Persistence**: Save/restore task state across restarts
5. **Metrics Collection**: Task execution metrics and monitoring

## Migration Timeline

- **Week 1-2**: Core infrastructure and critical tasks (pricing, premium)
- **Week 3-4**: Blockchain transaction tasks (EVM, Bitcoin)
- **Week 5-6**: Protocol and external service tasks
- **Week 7-8**: Testing, optimization, and deployment

This migration ensures rotki2 has a robust, modern async task management system that scales better and integrates seamlessly with the new async architecture.