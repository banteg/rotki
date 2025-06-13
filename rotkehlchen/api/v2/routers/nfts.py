"""NFT router for NFT-related endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from rotkehlchen.api.v2.dependencies import (
    get_chains_aggregator,
    get_data_handler,
    get_db_connection,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.nfts import NFTService
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.db.filtering import NFTFilterQuery
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.data_handler import DataHandler

router = APIRouter()


class NFTResponse(BaseModel):
    """Response model for NFT operations"""
    result: dict[str, Any]
    message: str = ''


class ManualPriceRequest(BaseModel):
    """Request model for manual NFT price"""
    asset: str = Field(..., description='NFT asset identifier')
    price: str = Field(..., description='Price of the NFT')
    price_asset: str = Field(..., description='Asset used for pricing')


class NFTFilterRequest(BaseModel):
    """Request model for NFT filtering"""
    owner_addresses: list[ChecksumEvmAddress] | None = None
    name: str | None = None
    collection_name: str | None = None
    ignored_assets: list[str] | None = None
    lps_handling: NftLpHandling = NftLpHandling.ALL_NFTS
    limit: int | None = None
    offset: int | None = None


def get_nft_service(
    db_connection: Annotated[DBConnection, Depends(get_db_connection)],
    chains_aggregator: Annotated['ChainsAggregator', Depends(get_chains_aggregator)],
    data_handler: Annotated['DataHandler', Depends(get_data_handler)],
) -> NFTService:
    """Get NFT service instance"""
    return NFTService(
        db_connection=db_connection,
        chains_aggregator=chains_aggregator,
        data_handler=data_handler,
    )


@router.get('/')
async def get_nfts(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
    async_query: bool = Query(False),
    ignore_cache: bool = Query(False),
) -> NFTResponse:
    """Get all NFT information for configured addresses"""
    # TODO: Implement async query support
    if async_query:
        return NFTResponse(
            result={'task_id': 'mock-task-id'},
            message='NFT query task started',
        )

    try:
        result = service.get_all_nfts(ignore_cache=ignore_cache)
        return NFTResponse(result=result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get NFTs: {e!s}',
        ) from e


@router.get('/balances')
async def get_nft_balances(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
    async_query: bool = Query(False),
    ignore_cache: bool = Query(False),
    owner_addresses: list[str] | None = Query(None),
    name: str | None = Query(None),
    collection_name: str | None = Query(None),
    ignored_assets: list[str] | None = Query(None),
    lps_handling: NftLpHandling = Query(NftLpHandling.ALL_NFTS),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
) -> NFTResponse:
    """Get NFT balances from database with filtering"""
    # TODO: Implement async query support
    if async_query:
        return NFTResponse(
            result={'task_id': 'mock-task-id'},
            message='NFT balance query task started',
        )

    # Convert addresses
    parsed_addresses = None
    if owner_addresses:
        try:
            from rotkehlchen.chain.evm.types import string_to_evm_address
            parsed_addresses = [string_to_evm_address(addr) for addr in owner_addresses]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid address format: {e!s}',
            ) from e

    # Create filter query
    filter_query = NFTFilterQuery(
        owner_addresses=parsed_addresses,
        name=name,
        collection_name=collection_name,
        ignored_assets=ignored_assets,
        lps_handling=lps_handling,
        limit=limit,
        offset=offset,
    )

    try:
        result = service.get_nft_balances(
            filter_query=filter_query,
            ignore_cache=ignore_cache,
        )
        return NFTResponse(result=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get NFT balances: {e!s}',
        ) from e


@router.post('/prices')
async def get_nfts_with_price(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
    lps_handling: NftLpHandling = NftLpHandling.ALL_NFTS,
) -> NFTResponse:
    """Get NFTs that have a price set"""
    try:
        result = service.get_nfts_with_price(lps_handling=lps_handling)
        return NFTResponse(result=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get NFTs with price: {e!s}',
        ) from e


@router.post('/prices/manual')
async def add_manual_nft_price(
    request: ManualPriceRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
) -> NFTResponse:
    """Add manual price for an NFT"""
    try:
        result = service.add_manual_nft_price(
            asset=request.asset,
            price=request.price,
            price_asset=request.price_asset,
        )
        return NFTResponse(result=result, message=result['message'])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to add manual NFT price: {e!s}',
        ) from e


@router.delete('/prices/manual/{asset}')
async def delete_manual_nft_price(
    asset: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
) -> NFTResponse:
    """Delete manual price for an NFT"""
    try:
        result = service.delete_manual_nft_price(asset=asset)
        return NFTResponse(result=result, message=result['message'])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to delete manual NFT price: {e!s}',
        ) from e
