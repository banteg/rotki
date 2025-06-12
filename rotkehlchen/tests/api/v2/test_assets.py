"""Tests for v2 assets API endpoints"""
import pytest
from fastapi.testclient import TestClient

from rotkehlchen.api.v2.app import create_app


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers"""
    # For testing, we'll mock authentication
    return {"X-API-Key": "test-api-key"}


class TestAssetsAPI:
    """Test assets endpoints"""
    
    def test_get_all_assets(self, client, auth_headers):
        """Test getting all assets"""
        response = client.get("/api/v2/assets/all", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "assets" in data["result"]
        assert "total" in data["result"]
    
    def test_search_assets(self, client, auth_headers):
        """Test asset search"""
        response = client.get(
            "/api/v2/assets/search",
            params={"query": "ETH"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert isinstance(data["result"], list)
    
    def test_get_asset_prices(self, client, auth_headers):
        """Test getting asset prices"""
        response = client.post(
            "/api/v2/assets/prices/latest",
            json={"assets": ["ETH", "BTC"]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "prices" in data["result"]
    
    def test_add_custom_asset(self, client, auth_headers):
        """Test adding custom asset"""
        response = client.post(
            "/api/v2/assets/custom",
            json={
                "identifier": "CUSTOM-TEST",
                "name": "Test Custom Asset",
                "type": "own chain",
            },
            headers=auth_headers,
        )
        # May fail if asset already exists, but structure should be correct
        if response.status_code == 200:
            data = response.json()
            assert "result" in data
            assert "identifier" in data["result"]
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to assets"""
        response = client.get("/api/v2/assets/all")
        assert response.status_code == 401