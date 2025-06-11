"""Base SQLAlchemy setup with gevent compatibility and SQLCipher support"""

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator, Optional

from gevent.lock import Semaphore
from sqlalchemy import MetaData, create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

if TYPE_CHECKING:
    from pathlib import Path

# Import SQLCipher dialect
from rotkehlchen.db.orm import sqlcipher  # noqa: F401

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    metadata = MetaData()


class GeventSafeDatabase:
    """Thread-safe database connection manager for gevent compatibility"""
    
    def __init__(
        self,
        db_path: 'Path',
        password: Optional[str] = None,
        timeout: int = 30000,
        cache_size: int = 10000,
        foreign_keys: bool = True,
    ):
        self.db_path = db_path
        self.password = password
        self.timeout = timeout
        self.cache_size = cache_size
        self.foreign_keys = foreign_keys
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker[Session]] = None
        self._semaphore = Semaphore()
        
    def get_engine(self) -> Engine:
        """Get or create the SQLAlchemy engine"""
        if self._engine is None:
            self._create_engine()
        return self._engine
    
    def _create_engine(self) -> None:
        """Create the SQLAlchemy engine with proper configuration"""
        if self.password:
            # SQLCipher connection for encrypted database
            connection_string = f"sqlite+pysqlcipher://:{self.password}@/{self.db_path}"
        else:
            # Regular SQLite connection
            connection_string = f"sqlite:///{self.db_path}"
        
        # Use StaticPool to maintain single connection for gevent compatibility
        self._engine = create_engine(
            connection_string,
            connect_args={
                "check_same_thread": False,
                "timeout": self.timeout / 1000,  # Convert ms to seconds
            },
            poolclass=StaticPool,
            echo=False,  # Set to True for SQL debugging
        )
        
        # Configure SQLite pragmas
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            
            # Basic SQLite configuration
            cursor.execute(f"PRAGMA foreign_keys={int(self.foreign_keys)}")
            cursor.execute(f"PRAGMA cache_size=-{self.cache_size}")
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # SQLCipher specific settings
            if self.password:
                cursor.execute("PRAGMA cipher_compatibility = 4")
                cursor.execute("PRAGMA kdf_iter = 256000")
                cursor.execute("PRAGMA cipher_page_size = 4096")
                cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
                cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
            
            cursor.close()
        
        # Create session factory
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions with gevent safety"""
        with self._semaphore:
            if self._session_factory is None:
                self.get_engine()
            
            session = self._session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    def execute_raw(self, query: str, params: Optional[dict[str, Any]] = None) -> Any:
        """Execute raw SQL query (for compatibility during migration)"""
        with self._semaphore:
            engine = self.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                conn.commit()
                return result
    
    def create_tables(self) -> None:
        """Create all tables defined in the ORM"""
        engine = self.get_engine()
        Base.metadata.create_all(engine)
    
    def close(self) -> None:
        """Close the database connection"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Singleton instances for each database
_user_db: Optional[GeventSafeDatabase] = None
_global_db: Optional[GeventSafeDatabase] = None
_transient_db: Optional[GeventSafeDatabase] = None


def get_user_db() -> GeventSafeDatabase:
    """Get the user database instance"""
    if _user_db is None:
        raise RuntimeError("User database not initialized")
    return _user_db


def get_global_db() -> GeventSafeDatabase:
    """Get the global database instance"""
    if _global_db is None:
        raise RuntimeError("Global database not initialized")
    return _global_db


def get_transient_db() -> GeventSafeDatabase:
    """Get the transient database instance"""
    if _transient_db is None:
        raise RuntimeError("Transient database not initialized")
    return _transient_db


def init_user_db(db_path: 'Path', password: str) -> GeventSafeDatabase:
    """Initialize the user database"""
    global _user_db
    _user_db = GeventSafeDatabase(db_path, password=password)
    return _user_db


def init_global_db(db_path: 'Path') -> GeventSafeDatabase:
    """Initialize the global database"""
    global _global_db
    _global_db = GeventSafeDatabase(db_path)
    return _global_db


def init_transient_db(db_path: 'Path') -> GeventSafeDatabase:
    """Initialize the transient database"""
    global _transient_db
    _transient_db = GeventSafeDatabase(db_path)
    return _transient_db