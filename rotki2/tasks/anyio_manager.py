"""Task manager using anyio for async task management."""
import logging
import traceback
from collections.abc import Callable
from typing import Any, TypeVar

import anyio
from anyio import CancelScope
from anyio.abc import TaskGroup

from rotkehlchen.errors.misc import GreenletKilledError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

T = TypeVar('T')


class AsyncTask:
    """Represents an async task with metadata."""
    
    def __init__(
        self,
        name: str,
        cancel_scope: CancelScope,
        exception_is_error: bool = True,
    ) -> None:
        self.name = name
        self.cancel_scope = cancel_scope
        self.exception_is_error = exception_is_error
        self.result: Any = None
        self.exception: Exception | None = None
        self.is_complete = False


class AnyioTaskManager:
    """A class to collect and manage async tasks spawned by various sources."""

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.msg_aggregator = msg_aggregator
        self.tasks: list[AsyncTask] = []
        self._task_group: TaskGroup | None = None

    async def __aenter__(self) -> 'AnyioTaskManager':
        """Enter async context and create task group."""
        self._task_group = await anyio.create_task_group().__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context and cleanup task group."""
        if self._task_group:
            await self._task_group.__aexit__(exc_type, exc_val, exc_tb)

    def add(self, task_name: str, cancel_scope: CancelScope, exception_is_error: bool) -> AsyncTask:
        """Add a task to track."""
        task = AsyncTask(task_name, cancel_scope, exception_is_error)
        self.tasks.append(task)
        return task

    async def spawn_and_track(
        self,
        after_seconds: float | None,
        task_name: str,
        exception_is_error: bool,
        method: Callable[..., Any],
        **kwargs: Any,
    ) -> AsyncTask:
        """Spawn a task and track it."""
        log.debug(f'Spawning task manager task "{task_name}"')
        
        if not self._task_group:
            msg = 'AnyioTaskManager must be used as an async context manager'
            raise RuntimeError(msg)

        async def wrapped_task() -> None:
            """Wrapper to handle task execution and error handling."""
            with anyio.CancelScope() as cancel_scope:
                task = self.add(task_name, cancel_scope, exception_is_error)
                try:
                    if after_seconds is not None:
                        await anyio.sleep(after_seconds)
                    task.result = await method(**kwargs)
                    task.is_complete = True
                except Exception as e:
                    task.exception = e
                    task.is_complete = True
                    await self._handle_task_exception(task)

        self._task_group.start_soon(wrapped_task)
        # Return the task object immediately
        return self.tasks[-1]

    async def clear(self) -> None:
        """Cancel all tracked tasks. To be called when logging out or shutting down."""
        for task in self.tasks:
            task.cancel_scope.cancel()
        self.tasks.clear()

    def clear_finished(self) -> None:
        """Remove all finished tracked tasks from the list."""
        self.tasks = [task for task in self.tasks if not task.is_complete]

    def has_task(self, name: str) -> bool:
        """Check if there is a running task with the given name."""
        for task in self.tasks:
            if not task.is_complete and task.name.startswith(name):
                return True
        return False

    async def _handle_task_exception(self, task: AsyncTask) -> None:
        """Handle exceptions from tasks."""
        if not task.exception:
            log.error('_handle_task_exception called without an exception')
            return

        if isinstance(task.exception, GreenletKilledError):
            log.debug(f'Task {task.name} was cancelled')
            return

        first_line = f'{task.name} died with exception: {task.exception}'
        if not task.exception_is_error:
            log.warning(f'{first_line} but that is not treated as an error')
            return

        exc_info = (
            type(task.exception),
            task.exception,
            task.exception.__traceback__,
        )
        msg = (
            f'{first_line}.\n'
            f'Exception Name: {exc_info[0]}\nException Info: {exc_info[1]}'
            f'\nTraceback:\n {"".join(traceback.format_tb(exc_info[2]))}'
        )
        log.error(msg)
        self.msg_aggregator.add_error(f'{first_line}. Check the logs for more details')