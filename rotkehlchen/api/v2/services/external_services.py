"""External services management service"""
from typing import Any

from rotkehlchen.api.v2.repositories.settings import SettingsRepository
from rotkehlchen.types import ExternalService


class ExternalServicesService:
    """Service for managing external service configurations"""

    def __init__(self) -> None:
        self.settings_repo = SettingsRepository()

    def get_all_services_status(self) -> dict[str, dict[str, Any]]:
        """Get the status of all external services"""
        # Get all available external services
        services_status = {}

        for service in ExternalService:
            service_name = service.value
            # Check if credentials exist for this service
            has_credentials = self._has_credentials(service)
            services_status[service_name] = {
                'name': service_name,
                'has_credentials': has_credentials,
            }

        return services_status

    def set_service_credentials(
        self,
        service: ExternalService,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Set credentials for an external service"""
        # Store credentials in settings based on what's provided
        if api_key is not None:
            key = f'external_service_{service.value}_api_key'
            self.settings_repo.set_setting(key, api_key)

        if username is not None:
            username_key = f'external_service_{service.value}_username'
            self.settings_repo.set_setting(username_key, username)

        if password is not None:
            password_key = f'external_service_{service.value}_password'
            self.settings_repo.set_setting(password_key, password)

    def delete_service_credentials(self, service: ExternalService) -> None:
        """Delete credentials for an external service"""
        # Remove credentials from settings
        key = f'external_service_{service.value}_api_key'
        self.settings_repo.set_setting(key, None)

        secret_key = f'external_service_{service.value}_api_secret'
        self.settings_repo.set_setting(secret_key, None)

    def _has_credentials(self, service: ExternalService) -> bool:
        """Check if credentials exist for a service"""
        key = f'external_service_{service.value}_api_key'
        api_key = self.settings_repo.get_setting(key)
        return api_key is not None and api_key != ''
