"""Async names router for ENS endpoints using async repository pattern"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import (
    get_async_ens_repository,
    get_chains_aggregator,
    require_logged_in_user,
)
from rotkehlchen.api.v2.repositories.async_ens import AsyncENSRepository
from rotkehlchen.api.v2.services.async_ens import AsyncENSService
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import InputError

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator

router = APIRouter()


class NamesResponse(BaseModel):
    """Response model for names operations"""
    result: dict[str, Any] | list[dict[str, Any]]
    message: str = ''


class ReverseEnsRequest(BaseModel):
    """Request model for reverse ENS lookup"""
    ethereum_addresses: list[str]
    ignore_cache: bool = False


class ResolveEnsRequest(BaseModel):
    """Request model for ENS resolution"""
    name: str
    ignore_cache: bool = False


async def get_async_ens_service(
    ens_repository: Annotated[AsyncENSRepository, Depends(get_async_ens_repository)],
    chains_aggregator: Annotated['ChainsAggregator', Depends(get_chains_aggregator)],
) -> AsyncENSService:
    """Get async ENS service instance"""
    return AsyncENSService(
        ens_repository=ens_repository,
        chains_aggregator=chains_aggregator,
    )


@router.post('/ens/reverse/async')
async def reverse_ens_lookup_async(
    request: ReverseEnsRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncENSService, Depends(get_async_ens_service)],
) -> NamesResponse:
    """Perform async reverse ENS lookup for Ethereum addresses"""
    # Parse addresses
    try:
        addresses = [string_to_evm_address(addr) for addr in request.ethereum_addresses]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid address format: {e!s}',
        ) from e

    try:
        result = await service.reverse_ens_lookup(
            ethereum_addresses=addresses,
            ignore_cache=request.ignore_cache,
        )
        # Convert result to string keys for JSON serialization
        serialized_result = {str(k): v for k, v in result.items()}
        return NamesResponse(result=serialized_result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to perform reverse ENS lookup: {e!s}',
        ) from e


@router.post('/ens/resolve/async')
async def resolve_ens_name_async(
    request: ResolveEnsRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncENSService, Depends(get_async_ens_service)],
) -> NamesResponse:
    """Async resolve ENS name to Ethereum address"""
    try:
        address = await service.resolve_ens_name(
            name=request.name,
            ignore_cache=request.ignore_cache,
        )
        return NamesResponse(result={'address': str(address) if address else None})
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to resolve ENS name: {e!s}',
        ) from e


@router.get('/avatars/ens/{ens_name}/update_time')
async def get_ens_avatar_update_time(
    ens_name: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncENSService, Depends(get_async_ens_service)],
) -> NamesResponse:
    """Get ENS avatar last update time"""
    try:
        update_time = await service.get_ens_avatar_update_time(ens_name=ens_name)
        return NamesResponse(result={'last_update': int(update_time)})
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get ENS avatar update time: {e!s}',
        ) from e
