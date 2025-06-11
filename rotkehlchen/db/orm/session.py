"""SQLAlchemy session management for rotkehlchen"""

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from rotkehlchen.db.orm.engines import (
    create_global_db_engine,
    create_transient_db_engine,
    create_user_db_engine,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = RotkehlchenLogsAdapter(__name__)


class DBSessionManager:
    """
    Manages SQLAlchemy sessions for rotkehlchen databases.
    
    This class handles session lifecycle, transaction management,
    and provides context managers for safe database operations.
    """
    
    def __init__(
        self,
        user_db_path: str,
        global_db_path: str,
        password: Optional[str] = None,
        echo_sql: bool = False,
    ):
        """
        Initialize session manager.
        
        Args:
            user_db_path: Path to user database
            global_db_path: Path to global database
            password: Optional password for user database encryption
            echo_sql: Whether to echo SQL statements (for debugging)
        """
        self.user_db_path = user_db_path
        self.global_db_path = global_db_path
        self.password = password
        self.echo_sql = echo_sql
        
        # Create engines
        self._user_engine = create_user_db_engine(
            path=user_db_path,
            password=password,
            echo=echo_sql,
        )
        self._global_engine = create_global_db_engine(
            path=global_db_path,
            echo=echo_sql,
        )
        self._transient_engine = create_transient_db_engine(echo=echo_sql)
        
        # Create session factories
        self._user_session_factory = scoped_session(
            sessionmaker(
                bind=self._user_engine,
                expire_on_commit=False,
                autoflush=False,
            )
        )
        self._global_session_factory = scoped_session(
            sessionmaker(
                bind=self._global_engine,
                expire_on_commit=False,
                autoflush=False,
            )
        )
        self._transient_session_factory = scoped_session(
            sessionmaker(
                bind=self._transient_engine,
                expire_on_commit=False,
                autoflush=False,
            )
        )
    
    @property
    def user_session(self) -> Session:
        """Get user database session"""
        return self._user_session_factory()
    
    @property
    def global_session(self) -> Session:
        """Get global database session"""
        return self._global_session_factory()
    
    @property
    def transient_session(self) -> Session:
        """Get transient database session"""
        return self._transient_session_factory()
    
    @contextmanager
    def user_db_session(self, commit: bool = True) -> Generator[Session, None, None]:
        """
        Context manager for user database operations.
        
        Args:
            commit: Whether to commit on successful exit
            
        Yields:
            Database session
        """
        session = self._user_session_factory()
        try:
            yield session
            if commit:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def global_db_session(self) -> Generator[Session, None, None]:
        """
        Context manager for global database operations (read-only).
        
        Yields:
            Database session
        """
        session = self._global_session_factory()
        try:
            yield session
        finally:
            session.close()
    
    @contextmanager
    def transient_db_session(self, commit: bool = True) -> Generator[Session, None, None]:
        """
        Context manager for transient database operations.
        
        Args:
            commit: Whether to commit on successful exit
            
        Yields:
            Database session
        """
        session = self._transient_session_factory()
        try:
            yield session
            if commit:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close_all(self) -> None:
        """Close all sessions and dispose engines"""
        # Remove all sessions
        self._user_session_factory.remove()
        self._global_session_factory.remove()
        self._transient_session_factory.remove()
        
        # Dispose engines
        self._user_engine.dispose()
        self._global_engine.dispose()
        self._transient_engine.dispose()
        
        logger.info("All database sessions closed and engines disposed")
    
    def execute_user_db_sql(self, sql: str, params: Optional[dict] = None) -> Any:
        """
        Execute raw SQL on user database.
        
        Args:
            sql: SQL statement to execute
            params: Optional parameters for the query
            
        Returns:
            Query result
        """
        with self.user_db_session() as session:
            result = session.execute(sql, params or {})
            return result.fetchall()
    
    def execute_global_db_sql(self, sql: str, params: Optional[dict] = None) -> Any:
        """
        Execute raw SQL on global database.
        
        Args:
            sql: SQL statement to execute
            params: Optional parameters for the query
            
        Returns:
            Query result
        """
        with self.global_db_session() as session:
            result = session.execute(sql, params or {})
            return result.fetchall()
    
    @contextmanager
    def transaction(self, session: Session) -> Generator[Session, None, None]:
        """
        Explicit transaction context manager.
        
        Args:
            session: Session to use for transaction
            
        Yields:
            Session within transaction
        """
        trans = session.begin()
        try:
            yield session
            trans.commit()
        except Exception:
            trans.rollback()
            raise
    
    def create_savepoint(self, session: Session, name: str) -> Any:
        """
        Create a savepoint in the current transaction.
        
        Args:
            session: Active session
            name: Savepoint name
            
        Returns:
            Savepoint object
        """
        return session.begin_nested()


# Global session manager instance
_session_manager: Optional[DBSessionManager] = None


def initialize_session_manager(
    user_db_path: str,
    global_db_path: str,
    password: Optional[str] = None,
    echo_sql: bool = False,
) -> DBSessionManager:
    """
    Initialize the global session manager.
    
    Args:
        user_db_path: Path to user database
        global_db_path: Path to global database
        password: Optional password for user database
        echo_sql: Whether to echo SQL statements
        
    Returns:
        Initialized session manager
    """
    global _session_manager
    
    if _session_manager is not None:
        _session_manager.close_all()
    
    _session_manager = DBSessionManager(
        user_db_path=user_db_path,
        global_db_path=global_db_path,
        password=password,
        echo_sql=echo_sql,
    )
    
    return _session_manager


def get_session_manager() -> DBSessionManager:
    """
    Get the global session manager.
    
    Returns:
        Session manager instance
        
    Raises:
        RuntimeError: If session manager not initialized
    """
    if _session_manager is None:
        raise RuntimeError("Session manager not initialized. Call initialize_session_manager first.")
    
    return _session_manager


@contextmanager
def db_session(db_type: str = 'user', commit: bool = True) -> Generator[Session, None, None]:
    """
    Convenience context manager for database sessions.
    
    Args:
        db_type: Type of database ('user', 'global', or 'transient')
        commit: Whether to commit on successful exit
        
    Yields:
        Database session
    """
    manager = get_session_manager()
    
    if db_type == 'user':
        with manager.user_db_session(commit=commit) as session:
            yield session
    elif db_type == 'global':
        with manager.global_db_session() as session:
            yield session
    elif db_type == 'transient':
        with manager.transient_db_session(commit=commit) as session:
            yield session
    else:
        raise ValueError(f"Unknown database type: {db_type}")