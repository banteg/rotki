"""Settings service for managing application settings"""
from typing import TYPE_CHECKING, Any, Sequence

from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import (
    CurrentPriceOracle,
    ExternalService,
    HistoricalPriceOracle,
    ModifiableDBSettings,
)

if TYPE_CHECKING:
    from rotki2.api.v2.repositories.settings import (
        MultiSettingsRepository,
        SettingsRepository,
    )
    from rotki2.api.v2.services.blockchain import BlockchainService
    from rotki2.api.v2.services.database import DatabaseService
    from rotki2.api.v2.services.oracles import OracleService


class SettingsService:
    """Service for managing application settings"""

    def __init__(
        self,
        settings_repo: 'SettingsRepository',
        multi_settings_repo: 'MultiSettingsRepository',
        blockchain_service: 'BlockchainService | None' = None,
        database_service: 'DatabaseService | None' = None,
        oracle_service: 'OracleService | None' = None,
    ):
        self.settings_repo = settings_repo
        self.multi_settings_repo = multi_settings_repo
        self.blockchain_service = blockchain_service
        self.database_service = database_service
        self.oracle_service = oracle_service

    async def get_settings(self) -> dict[str, Any]:
        """Get all application settings"""
        settings = await self.settings_repo.get_all_settings()
        
        # Add premium status if available
        if self.database_service:
            settings['have_premium'] = await self.database_service.have_premium()
            
        return settings

    async def update_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Update application settings"""
        # Validate settings before updating
        validated_settings = self._validate_settings(settings)

        # Update settings
        await self.settings_repo.update_settings(validated_settings)

        # Return updated settings
        return await self.get_settings()

    async def set_settings(self, settings: ModifiableDBSettings) -> tuple[bool, str]:
        """Set settings following the logic from rotkehlchen.py
        
        Returns (success, error_message)
        """
        # Handle KSM RPC endpoint
        if settings.ksm_rpc_endpoint is not None and self.blockchain_service:
            result, msg = await self.blockchain_service.set_ksm_rpc_endpoint(settings.ksm_rpc_endpoint)
            if not result:
                return False, msg
        
        # Handle DOT RPC endpoint
        if settings.dot_rpc_endpoint is not None and self.blockchain_service:
            result, msg = await self.blockchain_service.set_dot_rpc_endpoint(settings.dot_rpc_endpoint)
            if not result:
                return False, msg
        
        # Handle Beacon RPC endpoint
        if settings.beacon_rpc_endpoint is not None and self.blockchain_service:
            result, msg = await self.blockchain_service.set_beacon_rpc_endpoint(settings.beacon_rpc_endpoint)
            if not result:
                return False, msg
        
        # Handle BTC derivation gap limit
        if settings.btc_derivation_gap_limit is not None and self.blockchain_service:
            await self.blockchain_service.set_btc_derivation_gap_limit(settings.btc_derivation_gap_limit)
        
        # Handle current price oracles
        if settings.current_price_oracles is not None:
            success, msg = await self._validate_and_set_oracles(
                oracle_type=CurrentPriceOracle,
                oracles=settings.current_price_oracles,
                is_current=True,
            )
            if not success:
                return False, msg
        
        # Handle historical price oracles
        if settings.historical_price_oracles is not None:
            success, msg = await self._validate_and_set_oracles(
                oracle_type=HistoricalPriceOracle,
                oracles=settings.historical_price_oracles,
                is_current=False,
            )
            if not success:
                return False, msg
        
        # Handle active modules
        if settings.active_modules is not None and self.blockchain_service:
            await self.blockchain_service.process_new_modules_list(settings.active_modules)
        
        # Save settings to database
        if self.database_service:
            await self.database_service.set_settings(settings)
        
        return True, ''

    async def get_setting(self, name: str) -> Any:
        """Get a specific setting value"""
        value = await self.settings_repo.get_setting(name)
        if value is None:
            raise InputError(f'Setting {name} not found')
        return value

    async def set_setting(self, name: str, value: Any) -> dict[str, Any]:
        """Set a specific setting value"""
        # Validate the setting
        validated_value = self._validate_setting(name, value)

        # Update the setting
        await self.settings_repo.set_setting(name, validated_value)

        return {'name': name, 'value': validated_value}

    async def get_main_currency(self) -> str:
        """Get the main currency setting"""
        return await self.settings_repo.get_main_currency()

    async def set_main_currency(self, currency: str) -> dict[str, str]:
        """Set the main currency"""
        # Validate currency code
        if not currency or len(currency) != 3:
            raise InputError('Currency must be a 3-letter code')

        currency = currency.upper()
        await self.settings_repo.set_main_currency(currency)

        return {'main_currency': currency}

    async def get_ui_floating_precision(self) -> int:
        """Get the UI floating precision setting"""
        return await self.settings_repo.get_ui_floating_precision()

    async def set_ui_floating_precision(self, precision: int) -> dict[str, int]:
        """Set the UI floating precision"""
        if not 0 <= precision <= 8:
            raise InputError('Precision must be between 0 and 8')

        await self.settings_repo.set_ui_floating_precision(precision)

        return {'ui_floating_precision': precision}

    async def get_active_modules(self) -> list[str]:
        """Get the list of active modules"""
        return await self.settings_repo.get_active_modules()

    async def set_active_modules(self, modules: list[str]) -> dict[str, list[str]]:
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

        await self.settings_repo.set_active_modules(modules)

        return {'active_modules': modules}

    async def is_module_active(self, module_name: str) -> bool:
        """Check if a specific module is active"""
        return await self.settings_repo.is_module_active(module_name)

    async def get_ignored_assets(self) -> list[str]:
        """Get the list of ignored assets"""
        return await self.settings_repo.get_ignored_assets()

    async def set_ignored_assets(self, assets: list[str]) -> dict[str, list[str]]:
        """Set the list of ignored assets"""
        await self.settings_repo.set_ignored_assets(assets)
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
    
    async def _validate_and_set_oracles(
        self,
        oracle_type: type[CurrentPriceOracle | HistoricalPriceOracle],
        oracles: Sequence[CurrentPriceOracle] | Sequence[HistoricalPriceOracle] | None,
        is_current: bool,
    ) -> tuple[bool, str]:
        """Validate and set price oracles"""
        if oracles is None:
            return True, ''
        
        # Check if Alchemy is enabled but no API key is set
        if (
            oracle_type.ALCHEMY in oracles and
            self.database_service and
            not await self.database_service.has_external_service_credentials(ExternalService.ALCHEMY)
        ):
            return False, (
                'You have enabled the Alchemy price oracle but you do not have an API key '
                'set. Please go to API Keys -> External Services and add one.'
            )
        
        # Set the oracles order
        if self.oracle_service:
            if is_current:
                await self.oracle_service.set_current_price_oracles_order(oracles)
            else:
                await self.oracle_service.set_historical_price_oracles_order(oracles)
        
        return True, ''
