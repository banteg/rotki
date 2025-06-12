"""Configuration for v2 API tests"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from rotkehlchen.api.v2.app import create_app
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.api.v2.dependencies import (
    get_rotkehlchen,
    get_chains_aggregator,
    get_exchange_manager,
    get_data_handler,
    get_db_connection,
    get_accountant,
    get_history_querying_manager,
    get_task_manager,
    get_rotki_notifier,
)
from rotkehlchen.db.drivers.gevent import DBConnection


@pytest.fixture
def mock_rotkehlchen():
    """Create a mock Rotkehlchen instance with all required attributes"""
    mock_rotki = MagicMock()
    mock_rotki.user_is_logged_in = True
    mock_rotki.data.username = 'testuser'
    mock_rotki.data.db = MagicMock()
    mock_rotki.chains_aggregator = MagicMock()
    mock_rotki.exchange_manager = MagicMock()
    mock_rotki.accountant = MagicMock()
    mock_rotki.task_manager = MagicMock()
    mock_rotki.history_querying_manager = MagicMock()
    mock_rotki.rotki_notifier = MagicMock()
    mock_rotki.addressbook_prioritizer = MagicMock()
    
    # Mock the database connection
    mock_db_conn = MagicMock(spec=DBConnection)
    mock_rotki.data.db.conn = mock_db_conn
    
    return mock_rotki


@pytest.fixture
def test_database():
    """Create test database"""
    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    # TODO: Initialize schema
    return engine


@pytest.fixture
def db_session(test_database):
    """Create database session"""
    with Session(test_database) as session:
        yield session


@pytest.fixture
def app(mock_rotkehlchen, db_session):
    """Create FastAPI app for testing with mocked dependencies"""
    app = create_app()
    
    # Override all the dependencies
    app.dependency_overrides[get_rotkehlchen] = lambda: mock_rotkehlchen
    app.dependency_overrides[get_chains_aggregator] = lambda: mock_rotkehlchen.chains_aggregator
    app.dependency_overrides[get_exchange_manager] = lambda: mock_rotkehlchen.exchange_manager
    app.dependency_overrides[get_data_handler] = lambda: mock_rotkehlchen.data
    app.dependency_overrides[get_db_connection] = lambda: mock_rotkehlchen.data.db.conn
    app.dependency_overrides[get_accountant] = lambda: mock_rotkehlchen.accountant
    app.dependency_overrides[get_history_querying_manager] = lambda: mock_rotkehlchen.history_querying_manager
    app.dependency_overrides[get_task_manager] = lambda: mock_rotkehlchen.task_manager
    app.dependency_overrides[get_rotki_notifier] = lambda: mock_rotkehlchen.rotki_notifier
    
    # Mock the user authentication
    async def mock_logged_in_user():
        return "testuser"
    
    from rotkehlchen.api.v2.dependencies import require_logged_in_user
    app.dependency_overrides[require_logged_in_user] = mock_logged_in_user
    
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Mock authentication headers"""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_auth(app, monkeypatch):
    """Mock authentication for tests"""
    async def mock_require_logged_in_user(*args, **kwargs):
        return "testuser"
    
    # Patch the authentication dependency
    monkeypatch.setattr(
        "rotkehlchen.api.v2.dependencies.require_logged_in_user",
        mock_require_logged_in_user,
    )
    return app
