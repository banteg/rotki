"""Async database connection and session management."""
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


def _setup_sqlite_pragma(dbapi_connection, connection_record, password: str | None = None):
    """Set up SQLite pragmas for optimal performance and SQLCipher if needed."""
    cursor = dbapi_connection.cursor()
    
    # If password is provided, this is a SQLCipher database
    if password:
        cursor.execute(f"PRAGMA key='{password}'")
        cursor.execute('PRAGMA cipher_compatibility = 4')
    
    cursor.execute('PRAGMA journal_mode=WAL')
    cursor.execute('PRAGMA synchronous=NORMAL')
    cursor.execute('PRAGMA temp_store=MEMORY')
    cursor.execute('PRAGMA cache_size=10000')
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


def create_async_db_engine(
    db_path: Path, 
    password: str | None = None,
    echo: bool = False,
) -> AsyncEngine:
    """Create an async database engine for SQLite/SQLCipher.
    
    Args:
        db_path: Path to the SQLite database file
        password: Optional password for SQLCipher encryption
        echo: Whether to log all SQL statements
        
    Returns:
        Configured AsyncEngine instance
    """
    # Use aiosqlcipher if password is provided, otherwise use aiosqlite
    if password:
        # For SQLCipher, we need to use a special connection string
        database_url = f'sqlite+aiosqlcipher:///{db_path}'
    else:
        database_url = f'sqlite+aiosqlite:///{db_path}'

    # Create engine with NullPool to avoid connection pooling issues with SQLite
    engine = create_async_engine(
        database_url,
        echo=echo,
        poolclass=NullPool,
        connect_args={
            'check_same_thread': False,
            'timeout': 30.0,
        },
    )

    # Set up SQLite pragmas when connections are created
    def setup_connection(dbapi_connection, connection_record):
        _setup_sqlite_pragma(dbapi_connection, connection_record, password)
    
    event.listen(engine.sync_engine, 'connect', setup_connection)

    return engine


def create_async_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory.
    
    Args:
        engine: The AsyncEngine to bind sessions to
        
    Returns:
        async_sessionmaker instance for creating sessions
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def get_async_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async database session.
    
    Args:
        session_factory: The session factory to create sessions from
        
    Yields:
        AsyncSession instance
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
