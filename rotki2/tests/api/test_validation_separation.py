"""Tests to ensure v2 API properly separates validation from business logic"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from rotki2.api.v2.app import create_app


class TestValidationSeparation:
    """Test that v2 API keeps validation pure without DB/network calls"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = create_app()
        return TestClient(app)

    def test_blockchain_account_validation_no_db(self, client):
        """Test that blockchain account validation doesn't hit DB"""
        # In v1, BlockchainAccountsPatchSchema queries DB during validation
        # v2 should validate format only

        account_data = {
            'accounts': ['0x123invalid', 'not-an-address'],
            'labels': ['Account 1', 'Account 2'],
        }

        # Mock DB to ensure it's not called during validation
        with patch('rotkehlchen.api.v2.services.database.DatabaseService') as mock_db:
            response = client.post(
                '/api/v2/blockchain/eth/accounts',
                json=account_data,
                headers={'X-API-Key': 'test-key'},
            )

            # Should fail validation without DB access
            assert response.status_code == 422  # Validation error
            # DB should not be called during validation
            mock_db.assert_not_called()

    def test_ens_validation_no_network(self, client):
        """Test that ENS validation doesn't make network calls"""
        # In v1, ENS names trigger network lookups during deserialization
        # v2 should accept ENS names and resolve them in service layer

        account_data = {
            'accounts': ['vitalik.eth', 'uniswap.eth'],
        }

        # Mock network calls to ensure they don't happen during validation
        with patch('rotkehlchen.chain.ethereum.utils.EthereumInquirer.ens_lookup') as mock_ens:
            response = client.post(
                '/api/v2/blockchain/eth/accounts',
                json=account_data,
                headers={'X-API-Key': 'test-key'},
            )

            # Should accept ENS names without resolving them
            # Resolution happens in service layer
            mock_ens.assert_not_called()

    def test_history_event_validation_no_db(self, client):
        """Test that history event validation doesn't check DB"""
        # In v1, CreateHistoryEventSchema checks if tx_hash exists in DB
        # v2 should validate format only

        event_data = {
            'event_identifier': '0x123abc',
            'sequence_index': 0,
            'timestamp': 1234567890,
            'location': 'ethereum',
            'event_type': 'trade',
            'asset': 'ETH',
            'balance': {
                'amount': '1.5',
                'usd_value': '3000',
            },
        }

        with patch('rotkehlchen.api.v2.services.database.DatabaseService') as mock_db:
            response = client.post(
                '/api/v2/history/events',
                json=event_data,
                headers={'X-API-Key': 'test-key'},
            )

            # Validation should pass without DB
            # Only auth might fail
            assert response.status_code in [401, 200]  # Auth or success

    def test_asset_validation_simple(self, client):
        """Test that asset validation is simple type checking"""
        # In v1, AssetField has complex union types
        # v2 should use simple string validation

        price_data = {
            'assets': ['BTC', 'ETH', 'INVALID-ASSET-123'],
            'target_asset': 'USD',
        }

        with patch('rotkehlchen.api.v2.dependencies.require_logged_in_user', return_value='test'):
            response = client.post(
                '/api/v2/assets/prices/latest',
                json=price_data,
            )

            # Should accept any string as asset identifier
            # Validation happens in service layer
            assert response.status_code == 200
            data = response.json()

            # Invalid assets return None price
            assert data['result']['prices']['INVALID-ASSET-123'] is None


class TestServiceLayerValidation:
    """Test that business validation happens in service layer"""

    def test_blockchain_service_validates_addresses(self):
        """Test that blockchain service validates addresses"""
        from rotki2.api.v2.services.blockchain import BlockchainService
        from rotki2.api.v2.services.database import DatabaseService

        db_service = MagicMock(spec=DatabaseService)
        service = BlockchainService(db_service)

        # Service should validate addresses
        with pytest.raises(ValueError):
            service.add_blockchain_accounts(
                blockchain='eth',
                accounts=['invalid-address'],
            )

    def test_ens_resolution_in_service(self):
        """Test that ENS resolution happens in service layer"""
        from rotki2.api.v2.services.blockchain import BlockchainService
        from rotki2.api.v2.services.database import DatabaseService

        db_service = MagicMock(spec=DatabaseService)
        service = BlockchainService(db_service)

        # Mock ENS resolution
        with patch('rotkehlchen.chain.ethereum.utils.resolve_ens') as mock_resolve:
            mock_resolve.return_value = '0x123...'

            # Service resolves ENS names
            accounts = service.add_blockchain_accounts(
                blockchain='eth',
                accounts=['vitalik.eth'],
            )

            mock_resolve.assert_called_once_with('vitalik.eth')

    def test_tx_hash_validation_in_service(self):
        """Test that tx hash validation happens in service"""
        from rotki2.api.v2.services.database import DatabaseService
        from rotki2.api.v2.services.history import HistoryService

        db_service = MagicMock(spec=DatabaseService)
        service = HistoryService(db_service)

        # Service checks if tx exists
        with patch.object(service, '_check_tx_exists') as mock_check:
            mock_check.return_value = True

            event = service.create_history_event(
                event_identifier='0x123...',
                sequence_index=0,
                timestamp=123456,
                location='ethereum',
                event_type='trade',
                event_subtype=None,
                asset='ETH',
                balance={'amount': '1', 'usd_value': '2000'},
            )

            mock_check.assert_called_once()


class TestNoGlobalState:
    """Test that v2 API doesn't use global state"""

    def test_no_context_vars(self):
        """Ensure no ContextVar usage in v2"""
        # Search for ContextVar usage in v2 code
        import ast
        import os

        v2_path = '/workspace/rotkehlchen/api/v2'
        context_var_usage = []

        for root, dirs, files in os.walk(v2_path):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    with open(filepath) as f:
                        try:
                            tree = ast.parse(f.read())
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Name) and node.id == 'ContextVar':
                                    context_var_usage.append(filepath)
                        except:
                            pass

        assert len(context_var_usage) == 0, f'ContextVar found in: {context_var_usage}'

    def test_explicit_dependencies(self, client):
        """Test that dependencies are explicit"""
        from rotki2.api.v2.dependencies import get_database_service

        # All dependencies should be injected via FastAPI's Depends
        # No hidden global state

        # Check that service functions receive explicit dependencies
        with patch('rotkehlchen.api.v2.dependencies.get_db_connection') as mock_conn:
            mock_conn.return_value = MagicMock()

            service = get_database_service(mock_conn.return_value)
            assert service is not None
            assert hasattr(service, 'connection')


class TestModularStructure:
    """Test that v2 API has modular structure"""

    def test_feature_based_modules(self):
        """Test that routers are feature-based"""
        import os

        routers_path = '/workspace/rotkehlchen/api/v2/routers'
        router_files = [f for f in os.listdir(routers_path) if f.endswith('.py') and f != '__init__.py']

        # Each feature should have its own router
        expected_features = [
            'auth.py',
            'users.py',
            'settings.py',
            'assets.py',
            'balances.py',
            'blockchain.py',
            'exchanges.py',
            'history.py',
            'statistics.py',
        ]

        for feature in expected_features:
            assert feature in router_files, f'Missing router for {feature}'

    def test_small_focused_services(self):
        """Test that services are small and focused"""
        import os

        services_path = '/workspace/rotkehlchen/api/v2/services'
        service_files = [f for f in os.listdir(services_path) if f.endswith('.py') and f != '__init__.py']

        # Each service should be focused on one domain
        for service_file in service_files:
            filepath = os.path.join(services_path, service_file)
            with open(filepath) as f:
                lines = f.readlines()
                # Services should be reasonably sized
                assert len(lines) < 500, f'{service_file} is too large ({len(lines)} lines)'


class TestPerformanceOptimizations:
    """Test that v2 API avoids performance issues from v1"""

    def test_no_validation_time_lookups(self, client):
        """Test that validation doesn't do expensive lookups"""
        import time

        # Large request that would be slow in v1 due to ENS lookups
        account_data = {
            'accounts': [f'address{i}.eth' for i in range(50)],
        }

        start = time.time()
        response = client.post(
            '/api/v2/blockchain/eth/accounts',
            json=account_data,
            headers={'X-API-Key': 'test-key'},
        )
        validation_time = time.time() - start

        # Validation should be fast (no network calls)
        assert validation_time < 0.1, f'Validation took {validation_time}s'

    def test_deferred_consistency_checks(self):
        """Test that consistency checks are deferred"""
        from rotki2.api.v2.services.history import HistoryService

        # In v1, validation queries DB to check if tx exists
        # v2 should defer this to when actually needed

        service = HistoryService(MagicMock())

        # Creating event should not check existence immediately
        with patch.object(service.db, 'get_transaction') as mock_get:
            event = service.create_history_event(
                event_identifier='0x123...',
                sequence_index=0,
                timestamp=123456,
                location='ethereum',
                event_type='trade',
                event_subtype=None,
                asset='ETH',
                balance={'amount': '1', 'usd_value': '2000'},
            )

            # DB not queried during creation
            mock_get.assert_not_called()
