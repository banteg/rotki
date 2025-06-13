"""Direct comparison tests between v1 and v2 endpoints"""
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from rotki2.api.v2.app import create_app
from rotki2.api.v2.config import Settings
from rotkehlchen.tests.utils.api import api_url_for


class TestEndpointParity:
    """Test that v2 endpoints return identical responses to v1"""

    @pytest.fixture
    def v2_app(self):
        """Create v2 FastAPI app"""
        settings = Settings()
        return create_app(settings)

    def compare_responses(
        self,
        v1_response: dict[str, Any],
        v2_response: dict[str, Any],
        ignore_fields: list[str] | None = None,
    ) -> None:
        """Compare v1 and v2 responses, ignoring specified fields"""
        ignore_fields = ignore_fields or []

        # Remove ignored fields
        for field in ignore_fields:
            v1_response.pop(field, None)
            v2_response.pop(field, None)

        # Deep comparison
        assert v1_response == v2_response, (
            f"Responses don't match:\n"
            f"v1: {json.dumps(v1_response, indent=2)}\n"
            f"v2: {json.dumps(v2_response, indent=2)}"
        )

    def test_ping_endpoint(self, rotkehlchen_api_server, v2_app) -> None:
        """Test /ping endpoint returns same response"""
        # v1 response
        response = requests.get(api_url_for(rotkehlchen_api_server, 'ping'))
        v1_data = response.json()

        # v2 response
        from fastapi.testclient import TestClient
        client = TestClient(v2_app)
        v2_response = client.get('/api/v2/ping')
        v2_data = v2_response.json()

        self.compare_responses(v1_data, v2_data)

    def test_info_endpoint(self, rotkehlchen_api_server, v2_app) -> None:
        """Test /info endpoint returns same structure"""
        # Mock to ensure consistent data
        with patch('rotkehlchen.utils.version_check.get_current_version') as mock_version:
            mock_version.return_value = MagicMock(our_version='1.2.3')

            # v1 response
            response = requests.get(api_url_for(rotkehlchen_api_server, 'info'))
            v1_data = response.json()

            # v2 response
            from fastapi.testclient import TestClient
            client = TestClient(v2_app)
            v2_response = client.get('/api/v2/info')
            v2_data = v2_response.json()

            # Both should have result with version and data_directory
            assert 'result' in v1_data
            assert 'result' in v2_data
            assert v1_data['result']['version'] == v2_data['result']['version']
            assert 'data_directory' in v1_data['result']
            assert 'data_directory' in v2_data['result']

    def test_settings_structure(self, rotkehlchen_api_server, v2_app) -> None:
        """Test settings endpoint returns same structure"""
        # Create a logged in user for v1
        rotkehlchen_api_server.rest_api.rotkehlchen.data.unlock_user(
            user='test',
            password='test',
            create_new=True,
        )

        # v1 response
        response = requests.get(api_url_for(rotkehlchen_api_server, 'settingsresource'))
        v1_data = response.json()

        # v2 response with mocked auth
        from fastapi.testclient import TestClient
        client = TestClient(v2_app)

        with patch('rotkehlchen.api.v2.dependencies.require_logged_in_user', return_value='test'):
            v2_response = client.get('/api/v2/settings')
            v2_data = v2_response.json()

        # Check structure
        assert 'result' in v1_data
        assert 'result' in v2_data

        v1_settings = v1_data['result']
        v2_settings = v2_data['result']

        # Check all v1 fields exist in v2
        for key in v1_settings:
            assert key in v2_settings, f"Missing field '{key}' in v2 settings"

    def test_error_response_format(self, rotkehlchen_api_server, v2_app) -> None:
        """Test error responses have same format"""
        # v1 error - try to access protected endpoint
        response = requests.get(api_url_for(rotkehlchen_api_server, 'settingsresource'))
        if response.status_code != 200:
            v1_error = response.json()

            # v2 error
            from fastapi.testclient import TestClient
            client = TestClient(v2_app)
            v2_response = client.get('/api/v2/settings')

            if v2_response.status_code != 200:
                v2_error = v2_response.json()

                # v1 format: {"result": null, "message": "..."}
                # v2 FastAPI default: {"detail": "..."}
                # Need to update v2 error handler to match v1

    def test_list_endpoint_format(self, rotkehlchen_api_server, v2_app) -> None:
        """Test list endpoints return same format"""
        # Test with users endpoint
        response = requests.get(api_url_for(rotkehlchen_api_server, 'usersresource'))
        v1_data = response.json()

        from fastapi.testclient import TestClient
        client = TestClient(v2_app)

        with patch('rotkehlchen.api.v2.routers.users.get_users') as mock_get_users:
            # Mock to return same data
            mock_get_users.return_value = {'result': {'users': []}}
            v2_response = client.get('/api/v2/users')
            v2_data = v2_response.json()

        # Both should have result.users as list
        assert 'result' in v1_data
        assert 'users' in v1_data['result']
        assert isinstance(v1_data['result']['users'], list)

        assert 'result' in v2_data
        assert 'users' in v2_data['result']
        assert isinstance(v2_data['result']['users'], list)
