"""Deprecation utilities for marking deprecated functions and methods."""
import functools
import warnings
from collections.abc import Callable
from typing import Any, TypeVar, cast

F = TypeVar('F', bound=Callable[..., Any])


def deprecated(reason: str = '', version: str = '') -> Callable[[F], F]:
    """Decorator to mark functions/methods as deprecated.
    
    Args:
        reason: Optional reason why the function is deprecated and what to use instead
        version: Optional version when the deprecation was introduced
    
    Example:
        @deprecated(reason="Use HistoryRepository.get_history_events() instead", version="2.0.0")
        def old_method():
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            message = f'Call to deprecated {func.__name__!r}'
            if version:
                message += f' (deprecated since version {version})'
            if reason:
                message += f'. {reason}'
            warnings.warn(
                message,
                category=DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return cast('F', wrapper)
    return decorator
