"""Configuration for v2 API tests"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from rotkehlchen.api.v2.app import create_app
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.db.drivers.gevent import DBConnection


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
def app(db_session):
    """Create FastAPI app for testing"""
    app = create_app()
    # Override database dependency
    app.state.db_session = db_session
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
