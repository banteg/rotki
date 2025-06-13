"""Statistics router for portfolio statistics endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from rotki2.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotki2.api.v2.services.database import DatabaseService
from rotki2.api.v2.services.statistics import StatisticsService

router = APIRouter()


class StatisticsResponse(BaseModel):
    """Response model for statistics operations"""
    result: Any
    message: str = ''


class NetValueQuery(BaseModel):
    """Query parameters for net value statistics"""
    from_timestamp: int = Field(0, ge=0)
    to_timestamp: int = Field(2147483647, ge=0)


class AssetBalanceQuery(BaseModel):
    """Query parameters for asset balance statistics"""
    asset: str
    from_timestamp: int = Field(0, ge=0)
    to_timestamp: int = Field(2147483647, ge=0)


def get_statistics_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> StatisticsService:
    """Get statistics service instance"""
    return StatisticsService(db_service)


@router.get('/netvalue')
async def get_netvalue_statistics(
    _: Annotated[str, Depends(require_logged_in_user)],
    statistics_service: Annotated[StatisticsService, Depends(get_statistics_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> StatisticsResponse:
    """Get net value statistics over time"""
    stats = statistics_service.get_netvalue_statistics(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )

    return StatisticsResponse(result=stats)


@router.get('/balance/{asset}')
async def get_asset_balance_statistics(
    asset: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    statistics_service: Annotated[StatisticsService, Depends(get_statistics_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> StatisticsResponse:
    """Get balance statistics for a specific asset"""
    stats = statistics_service.get_asset_balance_statistics(
        asset=asset,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )

    return StatisticsResponse(result=stats)


@router.get('/value_distribution')
async def get_value_distribution(
    _: Annotated[str, Depends(require_logged_in_user)],
    statistics_service: Annotated[StatisticsService, Depends(get_statistics_service)],
) -> StatisticsResponse:
    """Get current value distribution across assets"""
    distribution = statistics_service.get_value_distribution()

    return StatisticsResponse(result=distribution)


@router.get('/location_distribution')
async def get_location_distribution(
    _: Annotated[str, Depends(require_logged_in_user)],
    statistics_service: Annotated[StatisticsService, Depends(get_statistics_service)],
) -> StatisticsResponse:
    """Get current value distribution across locations"""
    distribution = statistics_service.get_location_distribution()

    return StatisticsResponse(result=distribution)


@router.post('/renderer')
async def render_statistics(
    _: Annotated[str, Depends(require_logged_in_user)],
    statistics_service: Annotated[StatisticsService, Depends(get_statistics_service)],
    template: str,
    data: dict[str, Any],
) -> StatisticsResponse:
    """Render statistics using a template"""
    rendered = statistics_service.render_statistics(template, data)

    return StatisticsResponse(result={'rendered': rendered})
