"""Test fixtures for ORM tests"""

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from rotkehlchen.db.orm.database import RotkehlchenDatabase
from rotkehlchen.db.orm.models import TransientDBBase, UserDBBase
from rotkehlchen.db.orm.repository_manager import RepositoryManager
from rotkehlchen.db.orm.session import DBSessionManager


@pytest.fixture
def temp_user_db_path():
    """Create temporary user database path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / 'test_user.db'


@pytest.fixture
def temp_global_db_path():
    """Create temporary global database path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test_global.db'
        # Create empty global db
        db_path.touch()
        yield db_path


@pytest.fixture
def in_memory_engine():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine('sqlite:///:memory:')
    UserDBBase.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session(in_memory_engine):
    """Create test database session"""
    connection = in_memory_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_repos(test_session):
    """Create repository manager for testing"""
    return RepositoryManager(test_session)


@pytest.fixture
def orm_database(temp_user_db_path, temp_global_db_path):
    """Create ORM database for testing"""
    # Create minimal global database structure
    global_engine = create_engine(f'sqlite:///{temp_global_db_path}')
    global_engine.execute('CREATE TABLE IF NOT EXISTS info (version INTEGER)')
    global_engine.dispose()

    # Create ORM database
    db = RotkehlchenDatabase(
        user_data_dir=temp_user_db_path.parent,
        password='test_password',
        echo_sql=False,
    )

    yield db

    db.close()


@pytest.fixture
def session_manager(temp_user_db_path, temp_global_db_path):
    """Create session manager for testing"""
    # Create minimal global database
    global_engine = create_engine(f'sqlite:///{temp_global_db_path}')
    global_engine.execute('CREATE TABLE IF NOT EXISTS info (version INTEGER)')
    global_engine.dispose()

    manager = DBSessionManager(
        user_db_path=str(temp_user_db_path),
        global_db_path=str(temp_global_db_path),
        password='test_password',
        echo_sql=False,
    )

    # Create tables
    UserDBBase.metadata.create_all(manager._user_engine)
    TransientDBBase.metadata.create_all(manager._transient_engine)

    yield manager

    manager.close_all()
