"""Unit of Work pattern for managing database transactions"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Optional, TypeVar

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from rotkehlchen.db.orm.base import GeventSafeDatabase

T = TypeVar('T')


class UnitOfWork:
    """
    Unit of Work pattern implementation for transaction management.

    Ensures that all database operations within a business transaction
    are committed together or rolled back on error.
    """

    def __init__(self, database: 'GeventSafeDatabase'):
        self.database = database
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        """Get the current session"""
        if self._session is None:
            raise RuntimeError('UnitOfWork must be used as context manager')
        return self._session

    def __enter__(self) -> 'UnitOfWork':
        """Enter the unit of work context"""
        self._session = self.database._session_factory()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the unit of work context"""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self._session.close()
        self._session = None

    def commit(self) -> None:
        """Commit the transaction"""
        if self._session:
            self._session.commit()

    def rollback(self) -> None:
        """Rollback the transaction"""
        if self._session:
            self._session.rollback()

    def flush(self) -> None:
        """Flush pending changes without committing"""
        if self._session:
            self._session.flush()

    @contextmanager
    def savepoint(self, name: Optional[str] = None) -> Generator[None, None, None]:
        """Create a savepoint for nested transactions"""
        if not self._session:
            raise RuntimeError('No active session')

        savepoint = self._session.begin_nested()
        try:
            yield
            savepoint.commit()
        except Exception:
            savepoint.rollback()
            raise


# Repository registry for easy access
class RepositoryRegistry:
    """Registry for accessing repositories within a unit of work"""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self._repositories: dict[type, Any] = {}

    def get_repository(self, repo_class: type[T]) -> T:
        """Get or create a repository instance"""
        if repo_class not in self._repositories:
            self._repositories[repo_class] = repo_class(self.uow.session)
        return self._repositories[repo_class]

    def __getattr__(self, name: str) -> Any:
        """Allow accessing repositories as attributes"""
        # Convert snake_case to PascalCase for class lookup
        class_name = ''.join(word.capitalize() for word in name.split('_'))
        # This would need to be implemented with proper imports
        raise NotImplementedError(f'Repository {class_name} not found')


