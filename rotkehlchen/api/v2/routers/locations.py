"""Locations router for managing locations"""
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from rotkehlchen.api.v2.dependencies import get_db_session, require_logged_in_user
from rotkehlchen.api.v2.services.locations import LocationsService

if TYPE_CHECKING:
    pass

router = APIRouter()


class LocationsResponse(BaseModel):
    """Response model for locations operations"""
    result: list[str] | dict[str, list[str]]
    message: str = ''


def get_locations_service(session: Session | None = None) -> LocationsService:
    """Get locations service instance"""
    return LocationsService(session)


@router.get('/all', response_model=LocationsResponse)
async def get_all_locations(
    _: Annotated[str, Depends(require_logged_in_user)],
) -> LocationsResponse:
    """Get all supported locations"""
    service = get_locations_service()
    locations = service.get_all_locations()
    
    return LocationsResponse(result=locations)


@router.post('/all', response_model=LocationsResponse)
async def get_all_locations_post(
    _: Annotated[str, Depends(require_logged_in_user)],
) -> LocationsResponse:
    """Get all supported locations (POST version)"""
    return await get_all_locations(_)


@router.get('/associated', response_model=LocationsResponse)
async def get_associated_locations(
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> LocationsResponse:
    """Get locations with associated data"""
    service = get_locations_service(session)
    associated = service.get_associated_locations()
    
    return LocationsResponse(result=associated)


@router.post('/associated', response_model=LocationsResponse)
async def get_associated_locations_post(
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> LocationsResponse:
    """Get locations with associated data (POST version)"""
    return await get_associated_locations(_, session)