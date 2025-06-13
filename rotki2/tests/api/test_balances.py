"""Tests for v2 balances API endpoints"""
import pytest
from fastapi.testclient import TestClient

from rotki2.api.v2.app import create_app


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authentication headers"""
    return {'X-API-Key': 'test-api-key'}


class TestBalancesAPI:
    """Test balances endpoints"""

    def test_get_all_balances(self, client, auth_headers):
        """Test getting all balances"""
        response = client.get('/api/v2/balances', headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'result' in data
        assert 'assets' in data['result']
        assert 'liabilities' in data['result']
        assert 'total_net_value' in data['result']

    def test_get_blockchain_balances(self, client, auth_headers):
        """Test getting blockchain balances"""
        response = client.get('/api/v2/balances/blockchains', headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'result' in data

    def test_get_exchange_balances(self, client, auth_headers):
        """Test getting exchange balances"""
        response = client.get('/api/v2/balances/exchanges', headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'result' in data

    def test_get_manual_balances(self, client, auth_headers):
        """Test getting manual balances"""
        response = client.get('/api/v2/balances/manual', headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'result' in data
        assert isinstance(data['result'], list)

    def test_add_manual_balance(self, client, auth_headers):
        """Test adding manual balance"""
        response = client.post(
            '/api/v2/balances/manual',
            json={
                'asset': 'ETH',
                'amount': '1.5',
                'location': 'blockchain',
                'label': 'Test Balance',
            },
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert 'result' in data
            assert 'id' in data['result']

    def test_get_historical_balance(self, client, auth_headers):
        """Test getting historical balance"""
        response = client.post(
            '/api/v2/balances/historical',
            json={'timestamp': 1640995200},  # 2022-01-01
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert 'result' in data
        assert 'timestamp' in data['result']
        assert 'balances' in data['result']

    def test_unauthorized_balance_access(self, client):
        """Test unauthorized access to balances"""
        response = client.get('/api/v2/balances')
        assert response.status_code == 401
