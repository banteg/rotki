"""Names router for ENS and addressbook endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from rotki2.api.v2.dependencies import (
    get_async_names_service,
    require_logged_in_user,
)
from rotki2.api.v2.services.async_names import AsyncNamesService
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import AddressbookType, OptionalChainAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.data_handler import DataHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

router = APIRouter()


class NamesResponse(BaseModel):
    """Response model for names operations"""
    result: dict[str, Any] | list[dict[str, Any]]
    message: str = ''


class ReverseEnsRequest(BaseModel):
    """Request model for reverse ENS lookup"""
    ethereum_addresses: list[str]
    ignore_cache: bool = False
    async_query: bool = False


class ResolveEnsRequest(BaseModel):
    """Request model for ENS resolution"""
    name: str
    ignore_cache: bool = False
    async_query: bool = False


class AddressbookEntry(BaseModel):
    """Model for addressbook entry"""
    address: str
    name: str
    blockchain: str | None = None


class AddressbookRequest(BaseModel):
    """Request model for addressbook operations"""
    entries: list[AddressbookEntry]


class AddressbookFilterRequest(BaseModel):
    """Request model for addressbook filtering"""
    address: str | None = None
    name: str | None = None
    blockchain: str | None = None
    limit: int | None = Field(None, ge=1)
    offset: int | None = Field(None, ge=0)


class SearchNamesRequest(BaseModel):
    """Request model for searching names"""
    addresses: list[dict[str, Any]]




@router.post('/ens/reverse')
async def reverse_ens_lookup(
    request: ReverseEnsRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncNamesService, Depends(get_async_names_service)],
) -> NamesResponse:
    """Perform reverse ENS lookup for Ethereum addresses"""
    # TODO: Implement async query support
    if request.async_query:
        return NamesResponse(
            result={'task_id': 'mock-task-id'},
            message='ENS reverse lookup task started',
        )

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
        return NamesResponse(result=result)
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


@router.post('/ens/resolve')
async def resolve_ens_name(
    request: ResolveEnsRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncNamesService, Depends(get_async_names_service)],
) -> NamesResponse:
    """Resolve ENS name to Ethereum address"""
    # TODO: Implement async query support
    if request.async_query:
        return NamesResponse(
            result={'task_id': 'mock-task-id'},
            message='ENS resolution task started',
        )

    try:
        address = await service.resolve_ens_names(
            name=request.name,
            ignore_cache=request.ignore_cache,
        )
        return NamesResponse(result={'address': address})
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


@router.get('/avatars/ens/{ens_name}')
async def get_ens_avatar(
    ens_name: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncNamesService, Depends(get_async_names_service)],
) -> NamesResponse:
    """Get ENS avatar URL"""
    try:
        avatar_url = await service.get_ens_avatar(ens_name=ens_name)
        return NamesResponse(result={'avatar_url': avatar_url})
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get ENS avatar: {e!s}',
        ) from e


@router.post('/')
async def search_names(
    request: SearchNamesRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncNamesService, Depends(get_async_names_service)],
) -> NamesResponse:
    """Search for names everywhere (ENS, addressbook, etc.)"""
    # Convert request format to OptionalChainAddress
    chain_addresses = []
    for addr_data in request.addresses:
        chain_address = OptionalChainAddress(
            address=addr_data.get('address'),
            blockchain=addr_data.get('blockchain'),
        )
        chain_addresses.append(chain_address)

    try:
        results = await service.search_names_everywhere(addresses=chain_addresses)
        return NamesResponse(result=results)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to search names: {e!s}',
        ) from e


@router.post('/addressbook/{book_type}')
async def get_addressbook_entries(
    book_type: str,
    filter_request: AddressbookFilterRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncNamesService, Depends(get_async_names_service)],
) -> NamesResponse:
    """Get addressbook entries"""
    # Parse book type
    try:
        book_type_enum = AddressbookType(book_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid addressbook type: {book_type}',
        ) from None

    # Create filter query
    filter_query = AddressbookFilterQuery(
        address=filter_request.address,
        name=filter_request.name,
        blockchain=filter_request.blockchain,
        limit=filter_request.limit,
        offset=filter_request.offset,
    )

    try:
        result = await service.get_addressbook_entries(
            book_type=book_type_enum,
            filter_query=filter_query,
        )
        return NamesResponse(result=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get addressbook entries: {e!s}',
        ) from e


@router.put('/addressbook/{book_type}')
async def add_addressbook_entries(
    book_type: str,
    request: AddressbookRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncNamesService, Depends(get_async_names_service)],
) -> NamesResponse:
    """Add entries to addressbook"""
    # Parse book type
    try:
        book_type_enum = AddressbookType(book_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid addressbook type: {book_type}',
        ) from None

    # Convert entries
    entries = [entry.model_dump() for entry in request.entries]

    try:
        result = await service.add_addressbook_entries(
            book_type=book_type_enum,
            entries=entries,
        )
        return NamesResponse(result=result, message=result['message'])
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to add addressbook entries: {e!s}',
        ) from e


@router.patch('/addressbook/{book_type}')
async def update_addressbook_entries(
    book_type: str,
    request: AddressbookRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncNamesService, Depends(get_async_names_service)],
) -> NamesResponse:
    """Update addressbook entries"""
    # Parse book type
    try:
        book_type_enum = AddressbookType(book_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid addressbook type: {book_type}',
        ) from None

    # Convert entries
    entries = [entry.model_dump() for entry in request.entries]

    try:
        result = await service.update_addressbook_entries(
            book_type=book_type_enum,
            entries=entries,
        )
        return NamesResponse(result=result, message=result['message'])
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to update addressbook entries: {e!s}',
        ) from e


class DeleteAddressbookRequest(BaseModel):
    """Request model for deleting addressbook entries"""
    addresses: list[dict[str, Any]]


@router.delete('/addressbook/{book_type}')
async def delete_addressbook_entries(
    book_type: str,
    request: DeleteAddressbookRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncNamesService, Depends(get_async_names_service)],
) -> NamesResponse:
    """Delete addressbook entries"""
    # Parse book type
    try:
        book_type_enum = AddressbookType(book_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid addressbook type: {book_type}',
        ) from None

    # Convert addresses to OptionalChainAddress
    chain_addresses = []
    for addr_data in request.addresses:
        chain_address = OptionalChainAddress(
            address=addr_data.get('address'),
            blockchain=addr_data.get('blockchain'),
        )
        chain_addresses.append(chain_address)

    try:
        result = await service.delete_addressbook_entries(
            book_type=book_type_enum,
            chain_addresses=chain_addresses,
        )
        return NamesResponse(result=result, message=result['message'])
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to delete addressbook entries: {e!s}',
        ) from e
