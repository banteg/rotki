"""Queried addresses router for managing blockchain address queries"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.queried_addresses import QueriedAddressesService

router = APIRouter()


class QueriedAddressesResponse(BaseModel):
    """Response model for queried addresses operations"""
    result: dict[str, Any]
    message: str = ''


class QueriedAddressesRequest(BaseModel):
    """Request model for managing queried addresses"""
    addresses: list[str]
    blockchain: str


def get_queried_addresses_service() -> QueriedAddressesService:
    """Get queried addresses service instance"""
    return QueriedAddressesService()


@router.get('/')
async def get_queried_addresses(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[QueriedAddressesService, Depends(get_queried_addresses_service)],
) -> QueriedAddressesResponse:
    """Get all queried addresses"""
    addresses = service.get_all_queried_addresses()
    
    return QueriedAddressesResponse(
        result={'addresses': addresses},
    )


@router.post('/')
async def add_queried_addresses(
    data: QueriedAddressesRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[QueriedAddressesService, Depends(get_queried_addresses_service)],
) -> QueriedAddressesResponse:
    """Add addresses to be queried"""
    try:
        added = service.add_queried_addresses(
            addresses=data.addresses,
            blockchain=data.blockchain,
        )
        
        return QueriedAddressesResponse(
            result={'added': added},
            message=f'Added {added} addresses for querying',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/')
async def remove_queried_addresses(
    data: QueriedAddressesRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[QueriedAddressesService, Depends(get_queried_addresses_service)],
) -> QueriedAddressesResponse:
    """Remove addresses from being queried"""
    try:
        removed = service.remove_queried_addresses(
            addresses=data.addresses,
            blockchain=data.blockchain,
        )
        
        return QueriedAddressesResponse(
            result={'removed': removed},
            message=f'Removed {removed} addresses from querying',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e