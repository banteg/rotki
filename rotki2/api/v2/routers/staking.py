"""Staking router for managing staking operations"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.staking import StakingService
from rotkehlchen.types import Timestamp

router = APIRouter()


class StakingResponse(BaseModel):
    """Response model for staking operations"""
    result: dict[str, Any]
    message: str = ''


class KrakenStakingRequest(BaseModel):
    """Request model for Kraken staking operations"""
    from_timestamp: Timestamp | None = None
    to_timestamp: Timestamp | None = None
    only_cache: bool = False


def get_staking_service() -> StakingService:
    """Get staking service instance"""
    return StakingService()


@router.get('/kraken')
async def get_kraken_staking(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[StakingService, Depends(get_staking_service)],
    from_timestamp: Timestamp | None = None,
    to_timestamp: Timestamp | None = None,
) -> StakingResponse:
    """Get Kraken staking information"""
    staking_info = service.get_kraken_staking_info(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )

    return StakingResponse(result=staking_info)


@router.post('/kraken')
async def query_kraken_staking(
    request_data: KrakenStakingRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[StakingService, Depends(get_staking_service)],
) -> StakingResponse:
    """Query Kraken staking information"""
    try:
        if request_data.only_cache:
            staking_info = service.get_kraken_staking_info(
                from_timestamp=request_data.from_timestamp,
                to_timestamp=request_data.to_timestamp,
            )
        else:
            staking_info = service.query_kraken_staking(
                from_timestamp=request_data.from_timestamp,
                to_timestamp=request_data.to_timestamp,
            )

        return StakingResponse(result=staking_info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to query Kraken staking: {e!s}',
        ) from e
