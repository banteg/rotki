"""Queried addresses router for managing blockchain address queries"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.queried_addresses import QueriedAddressesService

router = APIRouter()


class QueriedAddressesResponse(BaseModel):
    """Response model for queried addresses operations"""
    result: dict[str, Any]
    message: str = ''


class QueriedAddressesRequest(BaseModel):
    """Request model for managing queried addresses"""
    addresses: list[str]
    blockchain: str


class QueriedAddressModuleRequest(BaseModel):
    """Request model for v1-compatible queried addresses"""
    module: str
    address: str


def get_queried_addresses_service() -> QueriedAddressesService:
    """Get queried addresses service instance"""
    return QueriedAddressesService()


@router.get('/')
async def get_queried_addresses(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[QueriedAddressesService, Depends(get_queried_addresses_service)],
) -> QueriedAddressesResponse:
    """Get all queried addresses per module - Compatible with v1 GET /api/1/queried_addresses"""
    addresses = service.get_all_queried_addresses()

    return QueriedAddressesResponse(
        result=addresses,  # v1 returns module->addresses mapping directly
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


# v1 compatibility endpoints
@router.put('/')
async def add_queried_address_v1(
    data: QueriedAddressModuleRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[QueriedAddressesService, Depends(get_queried_addresses_service)],
) -> QueriedAddressesResponse:
    """Add a queried address for a module - Compatible with v1 PUT /api/1/queried_addresses"""
    try:
        success = service.add_queried_address_for_module(
            module=data.module,
            address=data.address,
        )

        return QueriedAddressesResponse(
            result={'success': success},
            message=f'Address {data.address} added to module {data.module}' if success else 'Failed to add address',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/')
async def remove_queried_address_v1(
    module: str,
    address: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[QueriedAddressesService, Depends(get_queried_addresses_service)],
) -> QueriedAddressesResponse:
    """Remove a queried address for a module - Compatible with v1 DELETE /api/1/queried_addresses"""
    try:
        success = service.remove_queried_address_for_module(
            module=module,
            address=address,
        )

        return QueriedAddressesResponse(
            result={'success': success},
            message=f'Address {address} removed from module {module}' if success else 'Failed to remove address',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
