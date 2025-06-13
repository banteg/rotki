"""Airdrops router for managing airdrop metadata"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.airdrops import AirdropsService

router = APIRouter()


class AirdropsResponse(BaseModel):
    """Response model for airdrops operations"""
    result: dict[str, Any]
    message: str = ''


def get_airdrops_service() -> AirdropsService:
    """Get airdrops service instance"""
    return AirdropsService()


@router.get('/metadata')
async def get_airdrop_metadata(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AirdropsService, Depends(get_airdrops_service)],
) -> AirdropsResponse:
    """Get metadata for all supported airdrops - Compatible with v1 GET /api/1/airdrops/metadata"""
    metadata = service.get_all_airdrop_metadata()

    return AirdropsResponse(result={'airdrops': metadata})


@router.post('/metadata')
async def post_airdrop_metadata(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AirdropsService, Depends(get_airdrops_service)],
) -> AirdropsResponse:
    """Get metadata for all supported airdrops (POST version)"""
    return await get_airdrop_metadata(_, service)
