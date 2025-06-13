"""Settings router for application settings management"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rotki2.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotki2.api.v2.services.database import DatabaseService

router = APIRouter()


class SettingsResponse(BaseModel):
    """Response model for settings operations"""
    result: dict[str, Any]
    message: str = ''


class SettingsUpdateRequest(BaseModel):
    """Request model for updating settings"""
    main_currency: str | None = None
    premium_should_sync: bool | None = None
    submit_usage_analytics: bool | None = None
    active_modules: list[str] | None = None
    frontend_settings: dict[str, Any] | None = None
    account_for_assets_movements: bool | None = None
    btc_derivation_gap_limit: int | None = None
    calculate_past_cost_basis: bool | None = None
    display_date_in_localtime: bool | None = None
    include_crypto2crypto: bool | None = None
    include_gas_costs: bool | None = None
    taxfree_after_period: int | None = None
    balance_save_frequency: int | None = None
    date_display_format: str | None = None
    thousand_separator: str | None = None
    decimal_separator: str | None = None
    currency_location: str | None = None
    max_log_size_mb: int | None = None
    max_log_backup_files: int | None = None
    sql_vm_instructions_cb: int | None = None


@router.get('/')
async def get_settings(
    _: Annotated[str, Depends(require_logged_in_user)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> SettingsResponse:
    """Get current user settings"""
    settings = db_service.get_settings()

    if settings:
        result = {
            'main_currency': settings.main_currency,
            'premium_should_sync': settings.premium_should_sync,
            'submit_usage_analytics': settings.submit_usage_analytics,
            'active_modules': settings.active_modules or [],
            'frontend_settings': settings.frontend_settings or {},
            'account_for_assets_movements': settings.account_for_assets_movements,
            'btc_derivation_gap_limit': settings.btc_derivation_gap_limit,
            'calculate_past_cost_basis': settings.calculate_past_cost_basis,
            'display_date_in_localtime': settings.display_date_in_localtime,
            'include_crypto2crypto': settings.include_crypto2crypto,
            'include_gas_costs': settings.include_gas_costs,
            'taxfree_after_period': settings.taxfree_after_period,
            'balance_save_frequency': settings.balance_save_frequency,
            'date_display_format': settings.date_display_format,
            'thousand_separator': settings.thousand_separator,
            'decimal_separator': settings.decimal_separator,
            'currency_location': settings.currency_location,
            'max_log_size_mb': settings.max_log_size_mb,
            'max_log_backup_files': settings.max_log_backup_files,
            'sql_vm_instructions_cb': settings.sql_vm_instructions_cb,
        }
    else:
        # Return default settings
        result = {
            'main_currency': 'USD',
            'premium_should_sync': False,
            'submit_usage_analytics': True,
            'active_modules': [],
            'frontend_settings': {},
            'account_for_assets_movements': True,
            'btc_derivation_gap_limit': 20,
            'calculate_past_cost_basis': True,
            'display_date_in_localtime': True,
            'include_crypto2crypto': True,
            'include_gas_costs': True,
            'taxfree_after_period': 0,
            'balance_save_frequency': 24,
            'date_display_format': '%Y-%m-%d %H:%M:%S %Z',
            'thousand_separator': ',',
            'decimal_separator': '.',
            'currency_location': 'after',
            'max_log_size_mb': 100,
            'max_log_backup_files': 5,
            'sql_vm_instructions_cb': 5000,
        }

    return SettingsResponse(result=result)


@router.patch('/')
async def update_settings(
    settings_update: SettingsUpdateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> SettingsResponse:
    """Update user settings"""
    update_dict = settings_update.model_dump(exclude_none=True)

    if not update_dict:
        return SettingsResponse(
            result={},
            message='No settings to update',
        )

    updated_settings = db_service.update_settings(update_dict)

    return SettingsResponse(
        result={'updated': list(update_dict.keys())},
        message='Settings updated successfully',
    )


@router.post('/')
async def update_settings_post(
    settings_update: SettingsUpdateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> SettingsResponse:
    """Update user settings (POST version)"""
    return await update_settings(settings_update, _, db_service)


# Configuration endpoints (alias for settings)
@router.get('/configuration')
async def get_configuration(
    _: Annotated[str, Depends(require_logged_in_user)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> SettingsResponse:
    """Get current configuration (alias for settings)"""
    return await get_settings(_, db_service)


@router.post('/configuration')
async def update_configuration(
    settings_update: SettingsUpdateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> SettingsResponse:
    """Update configuration (alias for settings)"""
    return await update_settings(settings_update, _, db_service)
