"""Anyio-based lockable mixin for replacing gevent locks."""
from typing import Any

import anyio


class LockableQueryMixIn:
    """A mixin for classes that need to use async locks for query protection."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        # Create anyio locks - these will work with the current async backend
        self.history_lock = anyio.Lock()
        self.balance_lock = anyio.Lock()
        self.query_lock = anyio.Lock()
        # Add other locks as needed based on the original implementation


class LockableTaskMixin:
    """A mixin for task-related locks."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self.task_lock = anyio.Lock()