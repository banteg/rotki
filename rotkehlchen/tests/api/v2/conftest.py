"""Test configuration for v2 API tests"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from rotkehlchen.api.v2.app import create_app
from rotkehlchen.api.v2.config import Settings
from rotkehlchen.api.v2.dependencies import get_db_session
from rotkehlchen.db.models.user.base import Base as UserBase
from rotkehlchen.db.models.globaldb.base import Base as GlobalBase
from rotkehlchen.db.models.transient.base import Base as TransientBase


@pytest.fixture
def test_settings():
    """Test settings for v2 API"""
    return Settings(
        data_dir='/tmp/test_rotki',
        db_password='test',
        cors_origins=['http://localhost:3000'],
    )


@pytest.fixture
def test_db():
    """Create test database"""
    # Create in-memory SQLite database
    engine = create_engine('sqlite:///:memory:')
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    UserBase.metadata.create_all(engine)
    GlobalBase.metadata.create_all(engine)
    TransientBase.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session


@pytest.fixture
def v2_app(test_settings, test_db):
    """Create v2 app with test configuration"""
    app = create_app(test_settings)
    
    # Override database dependency
    def get_test_db():
        return test_db
    
    app.dependency_overrides[get_db_session] = get_test_db
    
    return app


@pytest.fixture
def v2_client(v2_app):
    """Create test client for v2 API"""
    return TestClient(v2_app)


@pytest.fixture
def authenticated_v2_client(v2_client):
    """Create authenticated test client"""
    # Mock authentication
    from unittest.mock import patch
    
    with patch('rotkehlchen.api.v2.dependencies.require_logged_in_user', return_value='test_user'):
        yield v2_client


@pytest.fixture
def mock_services():
    """Mock services for testing"""
    from unittest.mock import MagicMock
    
    return {
        'auth_service': MagicMock(),
        'database_service': MagicMock(),
        'assets_service': MagicMock(),
        'balances_service': MagicMock(),
        'blockchain_service': MagicMock(),
        'exchange_service': MagicMock(),
        'history_service': MagicMock(),
        'statistics_service': MagicMock(),
    }