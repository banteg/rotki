"""Oracles router for managing price oracles"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.oracles import OraclesService

router = APIRouter()


class OraclesResponse(BaseModel):
    """Response model for oracles operations"""
    result: dict[str, Any] | list[str]
    message: str = ''


class OracleCacheCreateRequest(BaseModel):
    """Request model for creating oracle cache"""
    from_asset: str
    to_asset: str
    purge_old: bool = False
    async_query: bool = False


class OracleCacheDeleteRequest(BaseModel):
    """Request model for deleting oracle cache"""
    from_asset: str
    to_asset: str


def get_oracles_service() -> OraclesService:
    """Get oracles service instance"""
    return OraclesService()


@router.get('/')
async def get_supported_oracles(
    oracles: Annotated[OraclesService, Depends(get_oracles_service)],
) -> OraclesResponse:
    """Get list of supported oracles - Compatible with v1 GET /api/1/oracles"""
    supported_oracles = oracles.get_supported_oracles()

    return OraclesResponse(result=supported_oracles)


@router.get('/{oracle}/cache')
async def get_oracle_cache(
    _: Annotated[str, Depends(require_logged_in_user)],
    oracles: Annotated[OraclesService, Depends(get_oracles_service)],
    oracle: str = Path(..., description='Oracle name'),
    async_query: bool = False,
) -> OraclesResponse:
    """Get cache for a specific oracle - Compatible with v1 GET /api/1/oracles/<oracle>/cache"""
    cache_data = oracles.get_oracle_cache(oracle, async_query)

    if cache_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Oracle {oracle} not found',
        )

    return OraclesResponse(result=cache_data)


@router.post('/{oracle}/cache')
async def create_oracle_cache(
    cache_data: OracleCacheCreateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    oracles: Annotated[OraclesService, Depends(get_oracles_service)],
    oracle: str = Path(..., description='Oracle name'),
) -> OraclesResponse:
    """Create cache for a specific oracle - Compatible with v1 POST /api/1/oracles/<oracle>/cache"""
    try:
        result = oracles.create_oracle_cache(
            oracle=oracle,
            from_asset=cache_data.from_asset,
            to_asset=cache_data.to_asset,
            purge_old=cache_data.purge_old,
            async_query=cache_data.async_query,
        )

        return OraclesResponse(
            result=result,
            message='Oracle cache created successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/{oracle}/cache')
async def delete_oracle_cache(
    cache_data: OracleCacheDeleteRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    oracles: Annotated[OraclesService, Depends(get_oracles_service)],
    oracle: str = Path(..., description='Oracle name'),
) -> OraclesResponse:
    """Delete cache for a specific oracle - Compatible with v1 DELETE /api/1/oracles/<oracle>/cache"""
    try:
        oracles.delete_oracle_cache(
            oracle=oracle,
            from_asset=cache_data.from_asset,
            to_asset=cache_data.to_asset,
        )

        return OraclesResponse(
            result={'success': True},
            message='Oracle cache deleted successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
