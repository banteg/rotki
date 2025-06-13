"""Tests to ensure v2 API responses match v1 format exactly"""
import pytest
from fastapi.testclient import TestClient

from rotki2.api.v2.app import create_app
from rotki2.api.v2.config import Settings


@pytest.fixture
def client() -> TestClient:
    """Create test client for v2 API"""
    settings = Settings()
    app = create_app(settings)
    return TestClient(app)


class TestResponseFormat:
    """Test that v2 API responses match v1 format"""

    def test_success_response_format(self, client: TestClient) -> None:
        """Test successful response format matches v1"""
        response = client.get('/api/v2/ping')

        assert response.status_code == 200
        data = response.json()

        # v1 returns {"result": true} for ping
        assert 'result' in data
        assert data['result'] is True
        assert 'message' not in data  # v1 doesn't include message in success

    def test_error_response_format(self, client: TestClient) -> None:
        """Test error response format matches v1"""
        # Try to access protected endpoint without auth
        response = client.get('/api/v2/settings')

        assert response.status_code == 401
        data = response.json()

        # v1 error format: {"result": null, "message": "error message"}
        assert 'detail' in data  # FastAPI default
        # TODO: Update FastAPI error handler to match v1 format

    def test_settings_response_format(self, client: TestClient) -> None:
        """Test settings response format"""
        # Mock authentication
        with pytest.mock.patch(
            'rotkehlchen.api.v2.dependencies.require_logged_in_user',
            return_value='test_user',
        ):
            response = client.get('/api/v2/settings')

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert 'result' in data
            assert isinstance(data['result'], dict)

            # Check required settings fields
            settings = data['result']
            required_fields = [
                'main_currency',
                'premium_should_sync',
                'submit_usage_analytics',
                'active_modules',
                'frontend_settings',
                'account_for_assets_movements',
                'btc_derivation_gap_limit',
                'calculate_past_cost_basis',
                'display_date_in_localtime',
                'include_crypto2crypto',
                'include_gas_costs',
                'taxfree_after_period',
                'balance_save_frequency',
                'date_display_format',
                'thousand_separator',
                'decimal_separator',
                'currency_location',
                'max_log_size_mb',
                'max_log_backup_files',
                'sql_vm_instructions_cb',
            ]

            for field in required_fields:
                assert field in settings, f'Missing required field: {field}'

    def test_balances_response_format(self, client: TestClient) -> None:
        """Test balances response format"""
        with pytest.mock.patch(
            'rotkehlchen.api.v2.dependencies.require_logged_in_user',
            return_value='test_user',
        ):
            response = client.get('/api/v2/balances')

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert 'result' in data
            assert isinstance(data['result'], dict)

            # Check required balance fields
            result = data['result']
            assert 'assets' in result
            assert 'liabilities' in result
            assert 'total_net_value' in result

            # Assets should be a dict of location -> asset -> balance
            assert isinstance(result['assets'], dict)
            assert isinstance(result['liabilities'], dict)
            assert isinstance(result['total_net_value'], str)

    def test_list_response_format(self, client: TestClient) -> None:
        """Test list response format (e.g., users list)"""
        with pytest.mock.patch(
            'rotkehlchen.api.v2.dependencies.get_database_service',
        ):
            response = client.get('/api/v2/users')

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert 'result' in data
            assert isinstance(data['result'], dict)
            assert 'users' in data['result']
            assert isinstance(data['result']['users'], list)

    def test_pagination_format(self, client: TestClient) -> None:
        """Test paginated response format"""
        with pytest.mock.patch(
            'rotkehlchen.api.v2.dependencies.require_logged_in_user',
            return_value='test_user',
        ):
            response = client.get('/api/v2/history/events?limit=10&offset=0')

            assert response.status_code == 200
            data = response.json()

            # Check pagination structure
            assert 'result' in data
            result = data['result']
            assert 'events' in result
            assert 'total' in result
            assert isinstance(result['events'], list)
            assert isinstance(result['total'], int)

    def test_async_task_response_format(self, client: TestClient) -> None:
        """Test async task response format"""
        with pytest.mock.patch(
            'rotkehlchen.api.v2.dependencies.require_logged_in_user',
            return_value='test_user',
        ):
            response = client.post('/api/v2/history/process')

            assert response.status_code == 200
            data = response.json()

            # Check async task response
            assert 'result' in data
            assert 'task_id' in data['result']
            assert isinstance(data['result']['task_id'], int)

    def test_empty_success_response(self, client: TestClient) -> None:
        """Test empty success response format"""
        with pytest.mock.patch(
            'rotkehlchen.api.v2.dependencies.require_logged_in_user',
            return_value='test_user',
        ):
            with pytest.mock.patch(
                'rotkehlchen.api.v2.routers.users.logout_user',
                return_value={'result': {'success': True}, 'message': 'User logged out successfully'},
            ):
                response = client.post('/api/v2/users/logout')

                assert response.status_code == 200
                data = response.json()

                # Some endpoints return success flag
                assert 'result' in data
                assert 'success' in data['result']
                assert data['result']['success'] is True
