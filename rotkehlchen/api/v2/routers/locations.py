"""Locations router for managing locations"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import get_db_session, require_logged_in_user
from rotkehlchen.constants.location import SUPPORTED_LOCATIONS
from rotkehlchen.types import Location
from sqlmodel import Session

if TYPE_CHECKING:
    pass

router = APIRouter()


class LocationsResponse(BaseModel):
    """Response model for locations operations"""
    result: list[str] | dict[str, list[str]]
    message: str = ''


@router.get('/all', response_model=LocationsResponse)
async def get_all_locations(
    _: Annotated[str, Depends(require_logged_in_user)],
) -> LocationsResponse:
    """Get all supported locations"""
    # Get all location values
    locations = [loc.value for loc in Location]
    
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
    # This would typically check which locations have data
    # For now, return a structure showing which locations have accounts
    
    from sqlmodel import select
    from rotkehlchen.db.models.blockchain_account import BlockchainAccount
    from rotkehlchen.db.models.user.accounts import UserCredentials
    
    # Get blockchains with accounts
    blockchain_query = select(BlockchainAccount.blockchain).distinct()
    blockchains = list(session.exec(blockchain_query).all())
    
    # Get exchanges with credentials
    exchange_query = select(UserCredentials.location).distinct()
    exchanges = list(session.exec(exchange_query).all())
    
    # Combine and categorize
    associated = {
        'blockchains': blockchains,
        'exchanges': exchanges,
        'other': [],  # Other locations like banks, etc.
    }
    
    return LocationsResponse(result=associated)


@router.post('/associated', response_model=LocationsResponse)
async def get_associated_locations_post(
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> LocationsResponse:
    """Get locations with associated data (POST version)"""
    return await get_associated_locations(_, session)