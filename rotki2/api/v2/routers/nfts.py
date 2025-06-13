"""NFT router for NFT-related endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from rotki2.api.v2.dependencies import (
    get_chains_aggregator,
    get_data_handler,
    get_db_connection,
    require_logged_in_user,
)
from rotki2.api.v2.services.nfts import NFTService
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


@router.get('/collections')
async def get_nft_collections(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
    owner_address: str | None = Query(None, description="Filter by owner address"),
) -> NFTResponse:
    """Get all NFT collections with metadata"""
    # This would aggregate NFTs by collection from the database
    return NFTResponse(
        result={
            'collections': [],
            'message': 'NFT collections endpoint - implementation pending',
        },
    )


@router.get('/collections/{collection_id}')
async def get_collection_details(
    collection_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
) -> NFTResponse:
    """Get detailed information about a specific NFT collection"""
    # This would query collection details from the database
    return NFTResponse(
        result={
            'collection_id': collection_id,
            'name': 'Collection Name',
            'description': 'Collection description',
            'nft_count': 0,
            'floor_price': '0',
            'message': 'Collection details endpoint - implementation pending',
        },
    )


@router.get('/transactions')
async def get_nft_transactions(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
    address: str | None = Query(None, description="Filter by address"),
    collection_id: str | None = Query(None, description="Filter by collection"),
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> NFTResponse:
    """Get NFT transaction history"""
    # This would query NFT transfer events from history_events
    return NFTResponse(
        result={
            'transactions': [],
            'message': 'NFT transactions endpoint - implementation pending',
        },
    )


@router.get('/statistics')
async def get_nft_statistics(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
    owner_address: str | None = Query(None, description="Filter by owner address"),
) -> NFTResponse:
    """Get NFT portfolio statistics"""
    # This would calculate NFT portfolio statistics
    return NFTResponse(
        result={
            'total_nfts': 0,
            'total_collections': 0,
            'total_value_usd': '0',
            'most_valuable_collection': None,
            'recent_activity': [],
            'message': 'NFT statistics endpoint - implementation pending',
        },
    )


@router.post('/refresh/{collection_id}')
async def refresh_collection_metadata(
    collection_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
) -> NFTResponse:
    """Refresh metadata for a specific collection"""
    # This would trigger a background task to refresh NFT metadata
    return NFTResponse(
        result={'task_id': 'placeholder-task-id'},
        message=f'Metadata refresh endpoint for collection {collection_id} - implementation pending',
    )


@router.get('/floor-prices')
async def get_floor_prices(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[NFTService, Depends(get_nft_service)],
    collection_ids: list[str] = Query(..., description="Collection IDs to get floor prices for"),
) -> NFTResponse:
    """Get floor prices for specified NFT collections"""
    # This would query floor prices from external APIs or cache
    floor_prices = {collection_id: '0' for collection_id in collection_ids}
    return NFTResponse(
        result={
            'floor_prices': floor_prices,
            'message': 'Floor prices endpoint - implementation pending',
        },
    )
