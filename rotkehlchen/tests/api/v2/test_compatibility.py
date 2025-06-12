"""Compatibility tests to ensure v2 API matches v1 behavior exactly"""
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from flask import Flask
from flask.testing import FlaskClient

from rotkehlchen.api.server import APIServer
from rotkehlchen.api.v2.app import create_app as create_v2_app


class APICompatibilityTester:
    """Test helper to compare v1 and v2 API responses"""

    def __init__(self, v1_client: FlaskClient, v2_client: TestClient):
        self.v1_client = v1_client
        self.v2_client = v2_client

    def assert_endpoints_match(
        self,
        method: str,
        v1_path: str,
        v2_path: str,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Assert that v1 and v2 endpoints return the same response"""
        # Make requests to both endpoints
        v1_response = getattr(self.v1_client, method.lower())(
            v1_path,
            data=data,
            json=json_data,
            query_string=params,
            headers=headers,
        )
        v2_response = getattr(self.v2_client, method.lower())(
            v2_path,
            data=data,
            json=json_data,
            params=params,
            headers=headers,
        )

        # Compare status codes
        assert v1_response.status_code == v2_response.status_code, (
            f"Status codes don't match: v1={v1_response.status_code}, "
            f"v2={v2_response.status_code}"
        )

        # Compare response bodies
        v1_json = v1_response.get_json()
        v2_json = v2_response.json()

        # Normalize responses (remove fields that might differ)
        self._normalize_response(v1_json)
        self._normalize_response(v2_json)

        assert v1_json == v2_json, (
            f"Response bodies don't match:\nv1={json.dumps(v1_json, indent=2)}\n"
            f"v2={json.dumps(v2_json, indent=2)}"
        )

    def _normalize_response(self, response: dict[str, Any]) -> None:
        """Normalize response by removing fields that might differ between versions"""
        # Remove version-specific fields
        if isinstance(response, dict):
            # Remove timing information that might differ
            response.pop('timestamp', None)
            response.pop('duration', None)
            
            # Recursively normalize nested structures
            for value in response.values():
                if isinstance(value, dict):
                    self._normalize_response(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._normalize_response(item)


@pytest.fixture
def v1_client(rotkehlchen_api_server: APIServer) -> FlaskClient:
    """Get Flask test client for v1 API"""
    return rotkehlchen_api_server.flask_app.test_client()


@pytest.fixture
def v2_client() -> TestClient:
    """Get FastAPI test client for v2 API"""
    app = create_v2_app()
    return TestClient(app)


@pytest.fixture
def api_tester(v1_client: FlaskClient, v2_client: TestClient) -> APICompatibilityTester:
    """Get API compatibility tester"""
    return APICompatibilityTester(v1_client, v2_client)


class TestUserEndpoints:
    """Test user management endpoints compatibility"""

    def test_get_users(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /users endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/users',
            v2_path='/api/v2/users',
        )

    def test_create_user(self, api_tester: APICompatibilityTester) -> None:
        """Test POST /users endpoint"""
        user_data = {
            'name': 'test_user',
            'password': 'test_password123',
            'initial_settings': {
                'main_currency': 'USD',
                'submit_usage_analytics': False,
            },
        }
        
        api_tester.assert_endpoints_match(
            method='POST',
            v1_path='/api/1/users',
            v2_path='/api/v2/users',
            json_data=user_data,
        )

    def test_user_login(self, api_tester: APICompatibilityTester) -> None:
        """Test POST /users/login endpoint"""
        login_data = {
            'name': 'test_user',
            'password': 'test_password123',
            'sync_approval': 'unknown',
        }
        
        api_tester.assert_endpoints_match(
            method='POST',
            v1_path='/api/1/users/test_user',  # v1 uses username in path for login
            v2_path='/api/v2/users/login',
            json_data=login_data,
        )


class TestSettingsEndpoints:
    """Test settings endpoints compatibility"""

    def test_get_settings(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /settings endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/settings',
            v2_path='/api/v2/settings',
        )

    def test_update_settings(self, api_tester: APICompatibilityTester) -> None:
        """Test PATCH /settings endpoint"""
        settings_data = {
            'main_currency': 'EUR',
            'submit_usage_analytics': True,
            'balance_save_frequency': 48,
        }
        
        # v1 uses PUT, v2 uses PATCH
        with patch.object(
            api_tester.v1_client,
            'put',
            wraps=api_tester.v1_client.put,
        ) as mock_put:
            api_tester.assert_endpoints_match(
                method='PUT',
                v1_path='/api/1/settings',
                v2_path='/api/v2/settings',
                json_data=settings_data,
            )


class TestAssetEndpoints:
    """Test asset endpoints compatibility"""

    def test_get_all_assets(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /assets/all endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/assets/all',
            v2_path='/api/v2/assets/all',
            params={'limit': 100, 'offset': 0},
        )

    def test_search_assets(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /assets/search endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/assets/search',
            v2_path='/api/v2/assets/search',
            params={'search_term': 'BTC', 'limit': 25},
        )

    def test_get_asset_prices(self, api_tester: APICompatibilityTester) -> None:
        """Test POST /assets/prices/latest endpoint"""
        price_data = {
            'assets': ['BTC', 'ETH', 'USDC'],
            'target_asset': 'USD',
        }
        
        api_tester.assert_endpoints_match(
            method='POST',
            v1_path='/api/1/assets/prices/latest',
            v2_path='/api/v2/assets/prices/latest',
            json_data=price_data,
        )


class TestBalanceEndpoints:
    """Test balance endpoints compatibility"""

    def test_get_all_balances(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /balances endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/balances',
            v2_path='/api/v2/balances',
            params={'save_data': False},
        )

    def test_get_blockchain_balances(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /balances/blockchains endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/balances/blockchains',
            v2_path='/api/v2/balances/blockchains',
        )

    def test_get_exchange_balances(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /balances/exchanges endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/balances/exchanges',
            v2_path='/api/v2/balances/exchanges',
        )

    def test_get_manual_balances(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /balances/manual endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/balances/manual',
            v2_path='/api/v2/balances/manual',
        )


class TestBlockchainEndpoints:
    """Test blockchain endpoints compatibility"""

    def test_get_supported_chains(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /blockchains/supported endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/blockchains/supported',
            v2_path='/api/v2/blockchain/supported',
        )

    def test_get_blockchain_accounts(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /blockchains/{blockchain}/accounts endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/blockchains/eth/accounts',
            v2_path='/api/v2/blockchain/eth/accounts',
        )

    def test_add_blockchain_accounts(self, api_tester: APICompatibilityTester) -> None:
        """Test POST /blockchains/{blockchain}/accounts endpoint"""
        account_data = {
            'accounts': ['0x123...', '0x456...'],
            'labels': ['Account 1', 'Account 2'],
        }
        
        api_tester.assert_endpoints_match(
            method='POST',
            v1_path='/api/1/blockchains/eth/accounts',
            v2_path='/api/v2/blockchain/eth/accounts',
            json_data=account_data,
        )


class TestExchangeEndpoints:
    """Test exchange endpoints compatibility"""

    def test_get_exchanges(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /exchanges endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/exchanges',
            v2_path='/api/v2/exchanges',
        )

    def test_add_exchange(self, api_tester: APICompatibilityTester) -> None:
        """Test POST /exchanges endpoint"""
        exchange_data = {
            'name': 'my_binance',
            'location': 'binance',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
        }
        
        api_tester.assert_endpoints_match(
            method='POST',
            v1_path='/api/1/exchanges',
            v2_path='/api/v2/exchanges',
            json_data=exchange_data,
        )

    def test_get_exchange_balances(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /exchanges/balances endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/exchanges/balances',
            v2_path='/api/v2/exchanges/balances',
        )


class TestHistoryEndpoints:
    """Test history endpoints compatibility"""

    def test_get_history_events(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /history/events endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/history/events',
            v2_path='/api/v2/history/events',
            params={
                'from_timestamp': 0,
                'to_timestamp': 2147483647,
                'limit': 100,
                'offset': 0,
            },
        )

    def test_process_history(self, api_tester: APICompatibilityTester) -> None:
        """Test POST /history/process endpoint"""
        api_tester.assert_endpoints_match(
            method='POST',
            v1_path='/api/1/history',
            v2_path='/api/v2/history/process',
            json_data={
                'from_timestamp': 0,
                'to_timestamp': 2147483647,
            },
        )


class TestStatisticsEndpoints:
    """Test statistics endpoints compatibility"""

    def test_get_netvalue_statistics(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /statistics/netvalue endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/statistics/netvalue',
            v2_path='/api/v2/statistics/netvalue',
            params={
                'from_timestamp': 0,
                'to_timestamp': 2147483647,
            },
        )

    def test_get_value_distribution(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /statistics/value_distribution endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/statistics/value_distribution',
            v2_path='/api/v2/statistics/value_distribution',
        )


class TestInfoEndpoints:
    """Test info and utility endpoints compatibility"""

    def test_ping(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /ping endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/ping',
            v2_path='/api/v2/ping',
        )

    def test_info(self, api_tester: APICompatibilityTester) -> None:
        """Test GET /info endpoint"""
        api_tester.assert_endpoints_match(
            method='GET',
            v1_path='/api/1/info',
            v2_path='/api/v2/info',
        )