"""SQLAlchemy engine configuration for rotkehlchen databases"""

import os
from typing import Any, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool, StaticPool

from rotkehlchen.db.drivers.gevent import GeventConnector
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = RotkehlchenLogsAdapter(__name__)


def _configure_sqlcipher(dbapi_connection: Any, connection_record: Any) -> None:
    """Configure SQLCipher settings on connection"""
    # Set SQLCipher pragmas
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA case_sensitive_like=ON")
    cursor.close()


def _configure_encrypted_sqlcipher(
    dbapi_connection: Any,
    connection_record: Any,
    password: str,
) -> None:
    """Configure SQLCipher with encryption"""
    cursor = dbapi_connection.cursor()
    # Set the encryption key
    cursor.execute(f"PRAGMA key='{password}'")
    # Verify the key is correct by querying
    cursor.execute("SELECT count(*) FROM sqlite_master")
    cursor.fetchone()
    # Set other pragmas
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA case_sensitive_like=ON")
    cursor.close()


def create_user_db_engine(
    path: str,
    password: Optional[str] = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    echo: bool = False,
) -> Engine:
    """
    Create SQLAlchemy engine for user database.
    
    Args:
        path: Path to the database file
        password: Optional password for SQLCipher encryption
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections
        echo: Whether to echo SQL statements
    
    Returns:
        Configured SQLAlchemy engine
    """
    # Use custom gevent connector
    connect_args = {
        'check_same_thread': False,
        'timeout': 30,
    }
    
    # Create engine with appropriate pooling
    if pool_size == 0:
        # Use NullPool for no connection pooling
        engine = create_engine(
            f"sqlite+pysqlcipher3:///{path}",
            connect_args=connect_args,
            poolclass=NullPool,
            echo=echo,
            module=GeventConnector,
        )
    else:
        # Use StaticPool for in-memory or single connection
        engine = create_engine(
            f"sqlite+pysqlcipher3:///{path}",
            connect_args=connect_args,
            poolclass=StaticPool,
            echo=echo,
            module=GeventConnector,
        )
    
    # Configure SQLCipher on each connection
    if password:
        event.listen(
            engine,
            "connect",
            lambda conn, rec: _configure_encrypted_sqlcipher(conn, rec, password)
        )
    else:
        event.listen(engine, "connect", _configure_sqlcipher)
    
    return engine


def create_global_db_engine(
    path: str,
    echo: bool = False,
) -> Engine:
    """
    Create SQLAlchemy engine for global database.
    
    The global database is read-only and doesn't use encryption.
    
    Args:
        path: Path to the global database file
        echo: Whether to echo SQL statements
    
    Returns:
        Configured SQLAlchemy engine
    """
    connect_args = {
        'check_same_thread': False,
        'timeout': 30,
    }
    
    # Create read-only engine
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args=connect_args,
        poolclass=StaticPool,
        echo=echo,
    )
    
    # Configure SQLite settings
    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA case_sensitive_like=ON")
        # Make it read-only
        cursor.execute("PRAGMA query_only=ON")
        cursor.close()
    
    return engine


def create_transient_db_engine(echo: bool = False) -> Engine:
    """
    Create SQLAlchemy engine for transient (in-memory) database.
    
    Args:
        echo: Whether to echo SQL statements
    
    Returns:
        Configured SQLAlchemy engine
    """
    # In-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
        echo=echo,
    )
    
    # Configure SQLite settings
    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA case_sensitive_like=ON")
        cursor.close()
    
    return engine


def test_engine_connection(engine: Engine) -> bool:
    """
    Test if engine can connect to database.
    
    Args:
        engine: SQLAlchemy engine to test
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            result.fetchone()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False


def dispose_engine(engine: Engine) -> None:
    """
    Properly dispose of engine and close all connections.
    
    Args:
        engine: Engine to dispose
    """
    engine.dispose()
    logger.debug("Database engine disposed")