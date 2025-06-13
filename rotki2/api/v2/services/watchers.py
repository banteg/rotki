"""Watchers service for premium features"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.errors.api import PremiumApiError, PremiumAuthenticationError
from rotkehlchen.errors.misc import RemoteError

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium


class WatchersService:
    """Service for managing watchers (premium feature)"""

    def __init__(self, premium: 'Premium | None' = None):
        self.premium = premium

    def _ensure_premium(self) -> 'Premium':
        """Ensure premium is available and active"""
        if self.premium is None:
            raise PremiumAuthenticationError('No premium subscription found')

        if not self.premium.is_active():
            raise PremiumAuthenticationError('Premium subscription is not active')

        return self.premium

    def get_watchers(self) -> dict[str, Any]:
        """Get all watchers from premium server"""
        premium = self._ensure_premium()

        try:
            result = premium.watcher_query(
                method='GET',
                data=None,
            )
            return result
        except RemoteError as e:
            raise PremiumApiError(f'Failed to fetch watchers: {e!s}') from e

    def add_watchers(self, watchers: list[dict[str, Any]]) -> dict[str, Any]:
        """Add new watchers to premium server"""
        premium = self._ensure_premium()

        # Validate watchers structure
        for watcher in watchers:
            if 'type' not in watcher or 'args' not in watcher:
                raise ValueError('Each watcher must have "type" and "args" fields')

        try:
            result = premium.watcher_query(
                method='PUT',
                data={'watchers': watchers},
            )
            return result
        except RemoteError as e:
            raise PremiumApiError(f'Failed to add watchers: {e!s}') from e

    def edit_watchers(self, watchers: list[dict[str, Any]]) -> dict[str, Any]:
        """Edit existing watchers on premium server"""
        premium = self._ensure_premium()

        # Validate watchers structure
        for watcher in watchers:
            if 'identifier' not in watcher:
                raise ValueError('Each watcher must have an "identifier" field for editing')
            if 'type' not in watcher or 'args' not in watcher:
                raise ValueError('Each watcher must have "type" and "args" fields')

        try:
            result = premium.watcher_query(
                method='PATCH',
                data={'watchers': watchers},
            )
            return result
        except RemoteError as e:
            raise PremiumApiError(f'Failed to edit watchers: {e!s}') from e

    def delete_watchers(self, identifiers: list[str]) -> dict[str, Any]:
        """Delete watchers from premium server"""
        premium = self._ensure_premium()

        if not identifiers:
            raise ValueError('At least one identifier must be provided')

        try:
            result = premium.watcher_query(
                method='DELETE',
                data={'watchers': identifiers},
            )
            return result
        except RemoteError as e:
            raise PremiumApiError(f'Failed to delete watchers: {e!s}') from e


class PremiumSyncService:
    """Service for premium data synchronization"""

    def __init__(self, premium: 'Premium | None' = None):
        self.premium = premium

    def _ensure_premium(self) -> 'Premium':
        """Ensure premium is available and active"""
        if self.premium is None:
            raise PremiumAuthenticationError('No premium subscription found')

        if not self.premium.is_active():
            raise PremiumAuthenticationError('Premium subscription is not active')

        return self.premium

    def sync_data(self, action: str) -> tuple[bool, str]:
        """Sync data with premium server
        
        Args:
            action: Either 'upload' or 'download'
        
        Returns:
            Tuple of (success, message)
        """
        premium = self._ensure_premium()

        if action not in ('upload', 'download'):
            raise ValueError('Action must be either "upload" or "download"')

        if not hasattr(premium, 'premium_sync_manager'):
            raise PremiumApiError('Premium sync manager not available')

        try:
            if action == 'upload':
                success, message = premium.premium_sync_manager.upload_data()
            else:  # download
                success, message = premium.premium_sync_manager.download_data()

            return success, message
        except Exception as e:
            return False, f'Sync failed: {e!s}'

    def get_sync_status(self) -> dict[str, Any]:
        """Get the current sync status"""
        premium = self._ensure_premium()

        if not hasattr(premium, 'premium_sync_manager'):
            raise PremiumApiError('Premium sync manager not available')

        try:
            # Get last sync times
            last_data_upload_ts = premium.premium_sync_manager.last_data_upload_ts
            last_data_download_ts = premium.premium_sync_manager.last_data_download_ts

            return {
                'last_upload': last_data_upload_ts,
                'last_download': last_data_download_ts,
                'syncing': False,  # Could be enhanced to track active sync
            }
        except Exception as e:
            raise PremiumApiError(f'Failed to get sync status: {e!s}') from e
