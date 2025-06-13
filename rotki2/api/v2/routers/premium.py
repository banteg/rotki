"""Premium router for premium subscription management"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.premium import PremiumService

router = APIRouter()


class PremiumResponse(BaseModel):
    """Response model for premium operations"""
    result: dict[str, Any]
    message: str = ''


class PremiumKeyRequest(BaseModel):
    """Request model for setting premium key"""
    api_key: str
    api_secret: str


class PremiumSyncRequest(BaseModel):
    """Request model for premium sync"""
    action: str  # 'upload' or 'download'
    async_query: bool = False


def get_premium_service() -> PremiumService:
    """Get premium service instance"""
    return PremiumService()


@router.get('/')
async def get_premium_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    premium: Annotated[PremiumService, Depends(get_premium_service)],
) -> PremiumResponse:
    """Get premium subscription status"""
    status = premium.get_premium_status()

    return PremiumResponse(result=status)


@router.post('/')
async def set_premium_credentials(
    credentials: PremiumKeyRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    premium: Annotated[PremiumService, Depends(get_premium_service)],
) -> PremiumResponse:
    """Set premium API credentials"""
    try:
        result = premium.set_premium_credentials(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
        )

        if result['success']:
            return PremiumResponse(
                result=result,
                message='Premium credentials set successfully',
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Failed to set premium credentials'),
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.delete('/')
async def remove_premium_credentials(
    _: Annotated[str, Depends(require_logged_in_user)],
    premium: Annotated[PremiumService, Depends(get_premium_service)],
) -> PremiumResponse:
    """Remove premium credentials"""
    premium.remove_premium_credentials()

    return PremiumResponse(
        result={'success': True},
        message='Premium credentials removed successfully',
    )


@router.get('/sync')
async def get_sync_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    premium: Annotated[PremiumService, Depends(get_premium_service)],
) -> PremiumResponse:
    """Get premium sync status"""
    sync_status = premium.get_sync_status()

    return PremiumResponse(result=sync_status)


@router.put('/sync')
async def perform_premium_sync(
    sync_request: PremiumSyncRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    premium: Annotated[PremiumService, Depends(get_premium_service)],
) -> PremiumResponse:
    """Perform premium data sync - Compatible with v1 PUT /api/1/premium/sync"""
    if not premium.is_premium_active():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail='Premium subscription required',
        )

    if sync_request.action not in ['upload', 'download']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Action must be either "upload" or "download"',
        )

    try:
        result = premium.sync_data(
            upload_data=(sync_request.action == 'upload'),
            download_data=(sync_request.action == 'download'),
        )

        return PremiumResponse(
            result=result,
            message=f'Premium {sync_request.action} completed',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Sync failed: {e!s}',
        ) from e
