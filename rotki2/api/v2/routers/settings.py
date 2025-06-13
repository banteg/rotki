"""Settings router for application settings management"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import (
    get_async_session,
    require_logged_in_user,
)
from rotki2.api.v2.repositories.settings import SettingsRepository, MultiSettingsRepository
from rotki2.api.v2.services.settings import SettingsService
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import ModifiableDBSettings
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


async def get_settings_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SettingsService:
    """Get settings service instance"""
    settings_repo = SettingsRepository(session)
    multi_settings_repo = MultiSettingsRepository(session)
    return SettingsService(
        settings_repo=settings_repo,
        multi_settings_repo=multi_settings_repo,
    )


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
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SettingsResponse:
    """Get current user settings"""
    try:
        settings = await settings_service.get_settings()
        return SettingsResponse(result=settings)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}"
        )


@router.patch('/')
async def update_settings(
    settings_update: SettingsUpdateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SettingsResponse:
    """Update user settings"""
    update_dict = settings_update.model_dump(exclude_none=True)

    if not update_dict:
        return SettingsResponse(
            result={},
            message='No settings to update',
        )

    try:
        # Convert to ModifiableDBSettings for proper validation
        modifiable_settings = ModifiableDBSettings(**update_dict)
        success, error_msg = await settings_service.set_settings(modifiable_settings)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        updated_settings = await settings_service.get_settings()
        return SettingsResponse(
            result=updated_settings,
            message='Settings updated successfully',
        )
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.post('/')
async def update_settings_post(
    settings_update: SettingsUpdateRequest,
    user: Annotated[str, Depends(require_logged_in_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SettingsResponse:
    """Update user settings (POST version)"""
    return await update_settings(settings_update, user, settings_service)


# Configuration endpoints (alias for settings)
@router.get('/configuration')
async def get_configuration(
    user: Annotated[str, Depends(require_logged_in_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SettingsResponse:
    """Get current configuration (alias for settings)"""
    return await get_settings(user, settings_service)


@router.post('/configuration')
async def update_configuration(
    settings_update: SettingsUpdateRequest,
    user: Annotated[str, Depends(require_logged_in_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SettingsResponse:
    """Update configuration (alias for settings)"""
    return await update_settings(settings_update, user, settings_service)
