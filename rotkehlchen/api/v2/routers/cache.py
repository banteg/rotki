"""Cache router for managing application caches"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.cache import CacheService

router = APIRouter()


class CacheResponse(BaseModel):
    """Response model for cache operations"""
    result: dict[str, Any]
    message: str = ''


def get_cache_service() -> CacheService:
    """Get cache service instance"""
    return CacheService()


@router.get('/{cache_type}/clear')
async def clear_cache(
    _: Annotated[str, Depends(require_logged_in_user)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    cache_type: str = Path(..., description="Type of cache to clear"),
) -> CacheResponse:
    """Clear a specific cache type"""
    valid_cache_types = cache_service.get_valid_cache_types()
    
    if cache_type not in valid_cache_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid cache type. Valid types are: {", ".join(valid_cache_types)}',
        )
    
    cache_service.clear_cache(cache_type)
    
    return CacheResponse(
        result={'cleared': True},
        message=f'{cache_type} cache cleared successfully',
    )


@router.post('/{cache_type}/clear')
async def clear_cache_post(
    _: Annotated[str, Depends(require_logged_in_user)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    cache_type: str = Path(..., description="Type of cache to clear"),
) -> CacheResponse:
    """Clear a specific cache type (POST version)"""
    return await clear_cache(_, cache_service, cache_type)


@router.delete('/{cache_type}/clear')
async def clear_cache_delete(
    _: Annotated[str, Depends(require_logged_in_user)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    cache_type: str = Path(..., description="Type of cache to clear"),
) -> CacheResponse:
    """Clear a specific cache type (DELETE version)"""
    return await clear_cache(_, cache_service, cache_type)


@router.put('/{cache_type}/clear')
async def clear_cache_put(
    _: Annotated[str, Depends(require_logged_in_user)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    cache_type: str = Path(..., description="Type of cache to clear"),
) -> CacheResponse:
    """Clear a specific cache type (PUT version)"""
    return await clear_cache(_, cache_service, cache_type)