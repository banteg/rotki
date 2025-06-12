"""Watchers router for premium watchers endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from rotkehlchen.api.v2.dependencies import get_rotkehlchen, require_logged_in_user
from rotkehlchen.api.v2.services.watchers import PremiumSyncService, WatchersService
from rotkehlchen.errors.api import PremiumApiError, PremiumAuthenticationError
from rotkehlchen.premium.premium import premium_create_and_verify

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

router = APIRouter()


class WatcherModel(BaseModel):
    """Model for a watcher"""
    type: str = Field(..., description="Type of the watcher")
    args: dict[str, Any] = Field(..., description="Arguments for the watcher")


class WatcherEditModel(WatcherModel):
    """Model for editing a watcher"""
    identifier: str = Field(..., description="Unique identifier of the watcher")


class WatchersResponse(BaseModel):
    """Response model for watchers operations"""
    result: dict[str, Any] | list[dict[str, Any]]
    message: str = ''


class WatchersAddRequest(BaseModel):
    """Request model for adding watchers"""
    watchers: list[WatcherModel]


class WatchersEditRequest(BaseModel):
    """Request model for editing watchers"""
    watchers: list[WatcherEditModel]


class WatchersDeleteRequest(BaseModel):
    """Request model for deleting watchers"""
    watchers: list[str] = Field(..., description="List of watcher identifiers to delete")


class PremiumSyncRequest(BaseModel):
    """Request model for premium sync"""
    action: str = Field(..., pattern="^(upload|download)$", description="Sync action: upload or download")


def get_watchers_service(
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> WatchersService:
    """Get watchers service instance with premium"""
    # Create and verify premium instance
    premium = None
    if rotkehlchen.data and rotkehlchen.data.db:
        premium = premium_create_and_verify(rotkehlchen.data.db)
    
    return WatchersService(premium=premium)


def get_premium_sync_service(
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> PremiumSyncService:
    """Get premium sync service instance"""
    # Create and verify premium instance
    premium = None
    if rotkehlchen.data and rotkehlchen.data.db:
        premium = premium_create_and_verify(rotkehlchen.data.db)
    
    return PremiumSyncService(premium=premium)


def require_premium_user():
    """Dependency to ensure user has active premium subscription"""
    async def check_premium(
        _: Annotated[str, Depends(require_logged_in_user)],
        service: Annotated[WatchersService, Depends(get_watchers_service)],
    ):
        try:
            service._ensure_premium()
        except PremiumAuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e),
            ) from e
    
    return Depends(check_premium)


@router.get('/')
async def get_watchers(
    _: Annotated[None, require_premium_user()],
    service: Annotated[WatchersService, Depends(get_watchers_service)],
) -> WatchersResponse:
    """Get all watchers"""
    try:
        result = service.get_watchers()
        return WatchersResponse(result=result)
    except PremiumApiError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get watchers: {str(e)}',
        ) from e


@router.put('/')
async def add_watchers(
    request: WatchersAddRequest,
    _: Annotated[None, require_premium_user()],
    service: Annotated[WatchersService, Depends(get_watchers_service)],
) -> WatchersResponse:
    """Add new watchers"""
    try:
        # Convert Pydantic models to dicts
        watchers_data = [w.model_dump() for w in request.watchers]
        result = service.add_watchers(watchers_data)
        return WatchersResponse(result=result, message='Watchers added successfully')
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except PremiumApiError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to add watchers: {str(e)}',
        ) from e


@router.patch('/')
async def edit_watchers(
    request: WatchersEditRequest,
    _: Annotated[None, require_premium_user()],
    service: Annotated[WatchersService, Depends(get_watchers_service)],
) -> WatchersResponse:
    """Edit existing watchers"""
    try:
        # Convert Pydantic models to dicts
        watchers_data = [w.model_dump() for w in request.watchers]
        result = service.edit_watchers(watchers_data)
        return WatchersResponse(result=result, message='Watchers edited successfully')
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except PremiumApiError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to edit watchers: {str(e)}',
        ) from e


@router.delete('/')
async def delete_watchers(
    request: WatchersDeleteRequest,
    _: Annotated[None, require_premium_user()],
    service: Annotated[WatchersService, Depends(get_watchers_service)],
) -> WatchersResponse:
    """Delete watchers"""
    try:
        result = service.delete_watchers(request.watchers)
        return WatchersResponse(result=result, message='Watchers deleted successfully')
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except PremiumApiError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to delete watchers: {str(e)}',
        ) from e


@router.put('/sync')
async def sync_premium_data(
    request: PremiumSyncRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[PremiumSyncService, Depends(get_premium_sync_service)],
) -> WatchersResponse:
    """Sync data with premium server"""
    try:
        success, message = service.sync_data(request.action)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message,
            )
        
        return WatchersResponse(
            result={'success': success},
            message=message,
        )
    except PremiumAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        ) from e
    except PremiumApiError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to sync data: {str(e)}',
        ) from e


@router.get('/sync/status')
async def get_sync_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[PremiumSyncService, Depends(get_premium_sync_service)],
) -> WatchersResponse:
    """Get premium sync status"""
    try:
        status_data = service.get_sync_status()
        return WatchersResponse(result=status_data)
    except PremiumAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        ) from e
    except PremiumApiError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get sync status: {str(e)}',
        ) from e