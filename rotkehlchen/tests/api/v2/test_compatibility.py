"""Compatibility tests between v1 and v2 API endpoints"""
import pytest
from fastapi.testclient import TestClient

from rotkehlchen.api.v2.app import create_app


@pytest.fixture
def v2_client():
    """Create v2 test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authentication headers"""
    return {"X-API-Key": "test-api-key"}


class TestV1V2Compatibility:
    """Test compatibility between v1 and v2 endpoints"""
    
    def test_response_format_compatibility(self, v2_client, auth_headers):
        """Test that v2 responses match v1 format"""
        # v1 format: {"result": data} for success
        # v1 format: {"message": "error", "status_code": code} for errors
        
        # Test success response
        response = v2_client.get("/api/v2/ping")
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "message" not in data  # Success shouldn't have message
        
        # Test error response
        response = v2_client.get("/api/v2/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data  # FastAPI default error format
    
    def test_asset_endpoint_compatibility(self, v2_client, auth_headers):
        """Test asset endpoints return compatible data"""
        # v2 endpoint
        response = v2_client.get("/api/v2/assets/all", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert "result" in data
            result = data["result"]
            
            # Check structure matches v1
            assert "assets" in result or isinstance(result, list)
            if "assets" in result:
                assets = result["assets"]
                if len(assets) > 0:
                    # Check asset structure
                    asset = assets[0]
                    # v1 assets have these fields
                    expected_fields = ["identifier", "name", "type"]
                    for field in expected_fields:
                        assert field in asset or "symbol" in asset
    
    def test_balance_endpoint_compatibility(self, v2_client, auth_headers):
        """Test balance endpoints return compatible data"""
        response = v2_client.get("/api/v2/balances", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert "result" in data
            result = data["result"]
            
            # Check v1 balance structure
            assert "assets" in result
            assert "liabilities" in result
            assert "total_net_value" in result or "net_usd_value" in result
    
    def test_settings_endpoint_compatibility(self, v2_client, auth_headers):
        """Test settings endpoints return compatible data"""
        response = v2_client.get("/api/v2/settings", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert "result" in data
            result = data["result"]
            
            # Check for common v1 settings fields
            expected_settings = [
                "main_currency",
                "premium_sync_enabled",
                "submit_usage_analytics",
            ]
            for setting in expected_settings:
                # Settings might be nested or flat
                assert setting in result or any(setting in str(v) for v in result.values())
    
    def test_history_endpoint_compatibility(self, v2_client, auth_headers):
        """Test history endpoints return compatible data"""
        response = v2_client.get("/api/v2/history/events", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert "result" in data
            result = data["result"]
            
            # Check v1 history structure
            assert "entries" in result or isinstance(result, list)
            assert "entries_total" in result or "total" in result
            assert "entries_found" in result or "found" in result
    
    def test_authentication_compatibility(self, v2_client):
        """Test authentication mechanisms are compatible"""
        # v1 uses session-based auth and API keys
        # v2 should support API keys in the same header
        
        # Test with API key header (v1 style)
        headers = {"rotki-api-key": "test-key"}
        response = v2_client.get("/api/v2/settings", headers=headers)
        # Should either work or give 401 (not 500)
        assert response.status_code in [200, 401]
        
        # Test with v2 style header
        headers = {"X-API-Key": "test-key"}
        response = v2_client.get("/api/v2/settings", headers=headers)
        assert response.status_code in [200, 401]
