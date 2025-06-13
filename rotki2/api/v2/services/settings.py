"""Settings service for managing application settings"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.errors.misc import InputError

if TYPE_CHECKING:
    from rotki2.api.v2.repositories.settings import (
        MultiSettingsRepository,
        SettingsRepository,
    )


class SettingsService:
    """Service for managing application settings"""

    def __init__(
        self,
        settings_repo: 'SettingsRepository',
        multi_settings_repo: 'MultiSettingsRepository',
    ):
        self.settings_repo = settings_repo
        self.multi_settings_repo = multi_settings_repo

    def get_settings(self) -> dict[str, Any]:
        """Get all application settings"""
        return self.settings_repo.get_all_settings()

    def update_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Update application settings"""
        # Validate settings before updating
        validated_settings = self._validate_settings(settings)

        # Update settings
        self.settings_repo.update_settings(validated_settings)

        # Return updated settings
        return self.get_settings()

    def get_setting(self, name: str) -> Any:
        """Get a specific setting value"""
        value = self.settings_repo.get_setting(name)
        if value is None:
            raise InputError(f'Setting {name} not found')
        return value

    def set_setting(self, name: str, value: Any) -> dict[str, Any]:
        """Set a specific setting value"""
        # Validate the setting
        validated_value = self._validate_setting(name, value)

        # Update the setting
        self.settings_repo.set_setting(name, validated_value)

        return {'name': name, 'value': validated_value}

    def get_main_currency(self) -> str:
        """Get the main currency setting"""
        return self.settings_repo.get_main_currency()

    def set_main_currency(self, currency: str) -> dict[str, str]:
        """Set the main currency"""
        # Validate currency code
        if not currency or len(currency) != 3:
            raise InputError('Currency must be a 3-letter code')

        currency = currency.upper()
        self.settings_repo.set_main_currency(currency)

        return {'main_currency': currency}

    def get_ui_floating_precision(self) -> int:
        """Get the UI floating precision setting"""
        return self.settings_repo.get_ui_floating_precision()

    def set_ui_floating_precision(self, precision: int) -> dict[str, int]:
        """Set the UI floating precision"""
        if not 0 <= precision <= 8:
            raise InputError('Precision must be between 0 and 8')

        self.settings_repo.set_ui_floating_precision(precision)

        return {'ui_floating_precision': precision}

    def get_active_modules(self) -> list[str]:
        """Get the list of active modules"""
        return self.settings_repo.get_active_modules()

    def set_active_modules(self, modules: list[str]) -> dict[str, list[str]]:
        """Set the list of active modules"""
        # Validate module names
        valid_modules = [
            'makerdao_dsr',
            'makerdao_vaults',
            'aave',
            'compound',
            'yearn_vaults',
            'uniswap',
            'balancer',
            'adex',
            'loopring',
            'eth2',
            'liquity',
            'pickle_finance',
            'convex_finance',
            'nfts',
        ]

        invalid_modules = [m for m in modules if m not in valid_modules]
        if invalid_modules:
            raise InputError(f'Invalid modules: {", ".join(invalid_modules)}')

        self.settings_repo.set_active_modules(modules)

        return {'active_modules': modules}

    def is_module_active(self, module_name: str) -> bool:
        """Check if a specific module is active"""
        return self.settings_repo.is_module_active(module_name)

    def get_ignored_assets(self) -> list[str]:
        """Get the list of ignored assets"""
        return self.settings_repo.get_ignored_assets()

    def set_ignored_assets(self, assets: list[str]) -> dict[str, list[str]]:
        """Set the list of ignored assets"""
        self.settings_repo.set_ignored_assets(assets)
        return {'ignored_assets': assets}

    def _validate_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Validate a dictionary of settings"""
        validated = {}

        for name, value in settings.items():
            validated[name] = self._validate_setting(name, value)

        return validated

    def _validate_setting(self, name: str, value: Any) -> Any:
        """Validate a single setting value"""
        # Add validation logic for specific settings
        if name == 'main_currency':
            if not isinstance(value, str) or len(value) != 3:
                raise InputError('main_currency must be a 3-letter string')
            return value.upper()

        elif name == 'ui_floating_precision':
            if not isinstance(value, int) or not 0 <= value <= 8:
                raise InputError('ui_floating_precision must be an integer between 0 and 8')
            return value

        elif name == 'active_modules':
            if not isinstance(value, list) or not all(isinstance(m, str) for m in value):
                raise InputError('active_modules must be a list of strings')
            return value

        elif name == 'ignored_assets':
            if not isinstance(value, list) or not all(isinstance(a, str) for a in value):
                raise InputError('ignored_assets must be a list of strings')
            return value

        # For other settings, return as-is
        return value
