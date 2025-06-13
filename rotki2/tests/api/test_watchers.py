"""Tests for the watchers endpoints"""
from unittest.mock import MagicMock, patch

import pytest

from rotki2.api.v2.routers.watchers import PremiumSyncService, WatchersService
from rotkehlchen.errors.api import PremiumApiError, PremiumAuthenticationError


@pytest.fixture
def mock_premium():
    """Create a mock premium instance"""
    premium = MagicMock()
    premium.is_active.return_value = True
    premium.watcher_query = MagicMock()
    premium.premium_sync_manager = MagicMock()
    premium.premium_sync_manager.last_data_upload_ts = 1234567890
    premium.premium_sync_manager.last_data_download_ts = 1234567891
    premium.premium_sync_manager.upload_data = MagicMock(return_value=(True, 'Upload successful'))
    premium.premium_sync_manager.download_data = MagicMock(return_value=(True, 'Download successful'))
    return premium


@pytest.fixture
def watchers_service(mock_premium):
    """Create a watchers service with mock premium"""
    return WatchersService(premium=mock_premium)


@pytest.fixture
def premium_sync_service(mock_premium):
    """Create a premium sync service with mock premium"""
    return PremiumSyncService(premium=mock_premium)


class TestWatchersService:
    """Test the watchers service"""

    def test_ensure_premium_no_premium(self):
        """Test that _ensure_premium raises error when no premium"""
        service = WatchersService(premium=None)
        with pytest.raises(PremiumAuthenticationError, match='No premium subscription found'):
            service._ensure_premium()

    def test_ensure_premium_inactive(self, mock_premium):
        """Test that _ensure_premium raises error when premium is inactive"""
        mock_premium.is_active.return_value = False
        service = WatchersService(premium=mock_premium)
        with pytest.raises(PremiumAuthenticationError, match='Premium subscription is not active'):
            service._ensure_premium()

    def test_get_watchers_success(self, watchers_service, mock_premium):
        """Test successful get_watchers"""
        expected_result = {
            'watchers': [
                {'identifier': '1', 'type': 'makervault', 'args': {'vault_id': 123}},
                {'identifier': '2', 'type': 'compound', 'args': {'address': '0xabc'}},
            ],
        }
        mock_premium.watcher_query.return_value = expected_result

        result = watchers_service.get_watchers()

        assert result == expected_result
        mock_premium.watcher_query.assert_called_once_with(method='GET', data=None)

    def test_get_watchers_remote_error(self, watchers_service, mock_premium):
        """Test get_watchers with remote error"""
        from rotkehlchen.errors.misc import RemoteError
        mock_premium.watcher_query.side_effect = RemoteError('Connection failed')

        with pytest.raises(PremiumApiError, match='Failed to fetch watchers: Connection failed'):
            watchers_service.get_watchers()

    def test_add_watchers_success(self, watchers_service, mock_premium):
        """Test successful add_watchers"""
        watchers_data = [
            {'type': 'makervault', 'args': {'vault_id': 123}},
            {'type': 'compound', 'args': {'address': '0xabc'}},
        ]
        expected_result = {'success': True}
        mock_premium.watcher_query.return_value = expected_result

        result = watchers_service.add_watchers(watchers_data)

        assert result == expected_result
        mock_premium.watcher_query.assert_called_once_with(
            method='PUT',
            data={'watchers': watchers_data},
        )

    def test_add_watchers_validation_error(self, watchers_service):
        """Test add_watchers with invalid data"""
        watchers_data = [
            {'args': {'vault_id': 123}},  # Missing type
        ]

        with pytest.raises(ValueError, match='Each watcher must have "type" and "args" fields'):
            watchers_service.add_watchers(watchers_data)

    def test_edit_watchers_success(self, watchers_service, mock_premium):
        """Test successful edit_watchers"""
        watchers_data = [
            {'identifier': '1', 'type': 'makervault', 'args': {'vault_id': 456}},
        ]
        expected_result = {'success': True}
        mock_premium.watcher_query.return_value = expected_result

        result = watchers_service.edit_watchers(watchers_data)

        assert result == expected_result
        mock_premium.watcher_query.assert_called_once_with(
            method='PATCH',
            data={'watchers': watchers_data},
        )

    def test_edit_watchers_validation_error(self, watchers_service):
        """Test edit_watchers with missing identifier"""
        watchers_data = [
            {'type': 'makervault', 'args': {'vault_id': 456}},  # Missing identifier
        ]

        with pytest.raises(ValueError, match='Each watcher must have an "identifier" field for editing'):
            watchers_service.edit_watchers(watchers_data)

    def test_delete_watchers_success(self, watchers_service, mock_premium):
        """Test successful delete_watchers"""
        identifiers = ['1', '2', '3']
        expected_result = {'success': True}
        mock_premium.watcher_query.return_value = expected_result

        result = watchers_service.delete_watchers(identifiers)

        assert result == expected_result
        mock_premium.watcher_query.assert_called_once_with(
            method='DELETE',
            data={'watchers': identifiers},
        )

    def test_delete_watchers_empty_list(self, watchers_service):
        """Test delete_watchers with empty list"""
        with pytest.raises(ValueError, match='At least one identifier must be provided'):
            watchers_service.delete_watchers([])


class TestPremiumSyncService:
    """Test the premium sync service"""

    def test_sync_data_upload_success(self, premium_sync_service, mock_premium):
        """Test successful data upload"""
        success, message = premium_sync_service.sync_data('upload')

        assert success is True
        assert message == 'Upload successful'
        mock_premium.premium_sync_manager.upload_data.assert_called_once()

    def test_sync_data_download_success(self, premium_sync_service, mock_premium):
        """Test successful data download"""
        success, message = premium_sync_service.sync_data('download')

        assert success is True
        assert message == 'Download successful'
        mock_premium.premium_sync_manager.download_data.assert_called_once()

    def test_sync_data_invalid_action(self, premium_sync_service):
        """Test sync_data with invalid action"""
        with pytest.raises(ValueError, match='Action must be either "upload" or "download"'):
            premium_sync_service.sync_data('invalid')

    def test_sync_data_no_sync_manager(self, mock_premium):
        """Test sync_data when premium_sync_manager is not available"""
        del mock_premium.premium_sync_manager
        service = PremiumSyncService(premium=mock_premium)

        with pytest.raises(PremiumApiError, match='Premium sync manager not available'):
            service.sync_data('upload')

    def test_sync_data_exception(self, premium_sync_service, mock_premium):
        """Test sync_data with exception during sync"""
        mock_premium.premium_sync_manager.upload_data.side_effect = Exception('Network error')

        success, message = premium_sync_service.sync_data('upload')

        assert success is False
        assert message == 'Sync failed: Network error'

    def test_get_sync_status_success(self, premium_sync_service):
        """Test successful get_sync_status"""
        result = premium_sync_service.get_sync_status()

        assert result == {
            'last_upload': 1234567890,
            'last_download': 1234567891,
            'syncing': False,
        }

    def test_get_sync_status_no_sync_manager(self, mock_premium):
        """Test get_sync_status when premium_sync_manager is not available"""
        del mock_premium.premium_sync_manager
        service = PremiumSyncService(premium=mock_premium)

        with pytest.raises(PremiumApiError, match='Premium sync manager not available'):
            service.get_sync_status()

    def test_get_sync_status_exception(self, premium_sync_service, mock_premium):
        """Test get_sync_status with exception"""
        mock_premium.premium_sync_manager.last_data_upload_ts = None  # Simulate attribute error

        with pytest.raises(PremiumApiError, match='Failed to get sync status'):
            premium_sync_service.get_sync_status()


@pytest.mark.asyncio
class TestWatchersEndpoints:
    """Test the watchers router endpoints"""

    @pytest.fixture
    def mock_rotkehlchen(self):
        """Create a mock Rotkehlchen instance"""
        rotki = MagicMock()
        rotki.data = MagicMock()
        rotki.data.db = MagicMock()
        return rotki

    async def test_get_watchers_endpoint(self, test_client, mock_rotkehlchen):
        """Test GET /watchers endpoint"""
        with patch('rotkehlchen.api.v2.routers.watchers.premium_create_and_verify') as mock_create_premium, \
             patch('rotkehlchen.api.v2.routers.watchers.get_rotkehlchen', return_value=mock_rotkehlchen):

            mock_premium = MagicMock()
            mock_premium.is_active.return_value = True
            mock_premium.watcher_query.return_value = {'watchers': []}
            mock_create_premium.return_value = mock_premium

            response = test_client.get('/api/v2/watchers')

            assert response.status_code == 200
            assert response.json() == {'result': {'watchers': []}, 'message': ''}

    async def test_add_watchers_endpoint(self, test_client, mock_rotkehlchen):
        """Test PUT /watchers endpoint"""
        with patch('rotkehlchen.api.v2.routers.watchers.premium_create_and_verify') as mock_create_premium, \
             patch('rotkehlchen.api.v2.routers.watchers.get_rotkehlchen', return_value=mock_rotkehlchen):

            mock_premium = MagicMock()
            mock_premium.is_active.return_value = True
            mock_premium.watcher_query.return_value = {'success': True}
            mock_create_premium.return_value = mock_premium

            request_data = {
                'watchers': [
                    {'type': 'makervault', 'args': {'vault_id': 123}},
                ],
            }

            response = test_client.put('/api/v2/watchers', json=request_data)

            assert response.status_code == 200
            assert response.json() == {
                'result': {'success': True},
                'message': 'Watchers added successfully',
            }

    async def test_sync_data_endpoint(self, test_client, mock_rotkehlchen):
        """Test PUT /watchers/sync endpoint"""
        with patch('rotkehlchen.api.v2.routers.watchers.premium_create_and_verify') as mock_create_premium, \
             patch('rotkehlchen.api.v2.routers.watchers.get_rotkehlchen', return_value=mock_rotkehlchen):

            mock_premium = MagicMock()
            mock_premium.is_active.return_value = True
            mock_premium.premium_sync_manager = MagicMock()
            mock_premium.premium_sync_manager.upload_data.return_value = (True, 'Upload successful')
            mock_create_premium.return_value = mock_premium

            request_data = {'action': 'upload'}

            response = test_client.put('/api/v2/watchers/sync', json=request_data)

            assert response.status_code == 200
            assert response.json() == {
                'result': {'success': True},
                'message': 'Upload successful',
            }

    async def test_watchers_no_premium(self, test_client, mock_rotkehlchen):
        """Test watchers endpoint without premium subscription"""
        with patch('rotkehlchen.api.v2.routers.watchers.premium_create_and_verify', return_value=None), \
             patch('rotkehlchen.api.v2.routers.watchers.get_rotkehlchen', return_value=mock_rotkehlchen):

            response = test_client.get('/api/v2/watchers')

            assert response.status_code == 402
            assert 'No premium subscription found' in response.json()['detail']
