"""Assets router for asset management endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.assets import AssetsService
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.types import Timestamp

router = APIRouter()


class AssetResponse(BaseModel):
    """Response model for asset operations"""
    result: Any
    message: str = ''


class CustomAssetRequest(BaseModel):
    """Request model for adding custom assets"""
    identifier: str
    name: str
    symbol: str
    asset_type: AssetType
    decimals: int | None = None


class AssetPriceRequest(BaseModel):
    """Request model for querying asset prices"""
    assets: list[str]
    target_asset: str = 'USD'
    timestamp: Timestamp | None = None


def get_assets_service() -> AssetsService:
    """Get assets service instance"""
    return AssetsService()


@router.post('/all')
async def query_all_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    asset_type: AssetType | None = None,
    limit: int = 500,
    offset: int = 0,
) -> AssetResponse:
    """Query all assets - Compatible with v1 POST /api/1/assets/all"""
    return await get_all_assets(_, assets_service, asset_type, limit, offset)


@router.get('/all')
async def get_all_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    asset_type: AssetType | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> AssetResponse:
    """Get all assets with optional filtering"""
    assets = assets_service.get_all_assets(
        asset_type=asset_type,
        limit=limit,
        offset=offset,
    )

    return AssetResponse(
        result={
            'assets': [
                {
                    'identifier': asset.identifier,
                    'name': asset.name,
                    'symbol': asset.symbol,
                    'asset_type': asset.asset_type.value,
                }
                for asset in assets
            ],
            'total': len(assets),
        },
    )


@router.get('/search')
async def search_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    search_term: str = Query(..., min_length=1),
    asset_type: AssetType | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
) -> AssetResponse:
    """Search for assets by name or symbol"""
    results = assets_service.search_assets(
        search_term=search_term,
        asset_type=asset_type,
        limit=limit,
    )

    return AssetResponse(
        result={
            'assets': [asset.identifier for asset in results],
            'total': len(results),
        },
    )


@router.post('/prices/latest')
async def get_latest_prices(
    price_request: AssetPriceRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get latest prices for multiple assets"""
    prices = {}
    target = Asset(price_request.target_asset)

    for asset_id in price_request.assets:
        try:
            asset = Asset(asset_id)
            price = assets_service.get_asset_price(
                asset=asset,
                target_asset=target,
                timestamp=price_request.timestamp,
            )
            prices[asset_id] = str(price)
        except UnknownAsset:
            prices[asset_id] = None

    return AssetResponse(
        result={
            'prices': prices,
            'target_asset': price_request.target_asset,
        },
    )


@router.put('/all')
async def add_asset_v1_compatible(
    asset_data: CustomAssetRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Add a new asset - Compatible with v1 PUT /api/1/assets/all"""
    return await add_custom_asset(asset_data, _, assets_service)


@router.post('/custom')
async def add_custom_asset(
    asset_data: CustomAssetRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Add a custom asset"""
    try:
        asset = assets_service.add_custom_asset(
            identifier=asset_data.identifier,
            name=asset_data.name,
            notes=f"Symbol: {asset_data.symbol}",
            custom_asset_type=asset_data.asset_type.value,
        )

        return AssetResponse(
            result={'identifier': asset.identifier},
            message='Custom asset added successfully',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.patch('/all')
async def edit_custom_asset(
    asset_data: CustomAssetRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Edit an existing custom asset - Compatible with v1 PATCH /api/1/assets/all"""
    try:
        asset = assets_service.edit_custom_asset(
            identifier=asset_data.identifier,
            name=asset_data.name,
            notes=f"Symbol: {asset_data.symbol}",
            custom_asset_type=asset_data.asset_type.value,
        )

        return AssetResponse(
            result={'identifier': asset.identifier},
            message='Custom asset updated successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/all')
async def delete_custom_asset(
    identifier: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Delete a custom asset - Compatible with v1 DELETE /api/1/assets/all"""
    try:
        assets_service.delete_custom_asset(identifier)
        
        return AssetResponse(
            result={'success': True},
            message=f'Custom asset {identifier} deleted successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get('/evm/erc20/{chain_id}/{address}')
async def get_erc20_token_info(
    chain_id: int,
    address: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get ERC20 token information"""
    token = assets_service.get_evm_token_info(address, chain_id)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Token not found',
        )

    return AssetResponse(
        result={
            'identifier': token.identifier,
            'address': token.evm_address,
            'chain_id': token.chain_id,
            'decimals': token.decimals,
            'name': token.name,
            'symbol': token.symbol,
        },
    )


@router.get('/')
async def get_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get user assets"""
    assets = assets_service.get_user_assets()
    return AssetResponse(result={'assets': assets})


@router.post('/')
async def post_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get user assets (POST version)"""
    return await get_assets(_, assets_service)


@router.get('/ignored')
async def get_ignored_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get ignored assets"""
    ignored = assets_service.get_ignored_assets()
    return AssetResponse(result={'assets': ignored})


@router.post('/ignored')
async def modify_ignored_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    assets: list[str],
    action: str = 'add',
) -> AssetResponse:
    """Add or remove ignored assets"""
    if action == 'add':
        assets_service.add_ignored_assets(assets)
    elif action == 'remove':
        assets_service.remove_ignored_assets(assets)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid action. Must be "add" or "remove"',
        )
    
    return AssetResponse(
        result={'success': True},
        message=f'Successfully {action}ed {len(assets)} assets',
    )


@router.get('/ignored/whitelist')
async def get_ignored_whitelist(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get ignored assets whitelist"""
    whitelist = assets_service.get_ignored_whitelist()
    return AssetResponse(result={'assets': whitelist})


@router.post('/ignored/whitelist')
async def modify_ignored_whitelist(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    assets: list[str],
    action: str = 'add',
) -> AssetResponse:
    """Add or remove assets from ignored whitelist"""
    if action == 'add':
        assets_service.add_to_ignored_whitelist(assets)
    elif action == 'remove':
        assets_service.remove_from_ignored_whitelist(assets)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid action. Must be "add" or "remove"',
        )
    
    return AssetResponse(
        result={'success': True},
        message=f'Successfully {action}ed {len(assets)} assets to/from whitelist',
    )


@router.get('/types')
async def get_asset_types(
    _: Annotated[str, Depends(require_logged_in_user)],
) -> AssetResponse:
    """Get all available asset types"""
    # Get all asset type values
    asset_types = [asset_type.value for asset_type in AssetType]
    return AssetResponse(result={'types': asset_types})


@router.post('/types')
async def post_asset_types(
    _: Annotated[str, Depends(require_logged_in_user)],
) -> AssetResponse:
    """Get all available asset types (POST version)"""
    return await get_asset_types(_)


@router.get('/user')
async def get_user_owned_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get assets owned by the user"""
    owned_assets = assets_service.get_user_owned_assets()
    return AssetResponse(result={'assets': owned_assets})


@router.post('/user')
async def post_user_owned_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get assets owned by the user (POST version)"""
    return await get_user_owned_assets(_, assets_service)


@router.get('/prices/latest/all')
async def get_all_latest_prices(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get latest prices for all known assets"""
    prices = assets_service.get_all_latest_prices()
    
    return AssetResponse(result=prices)


@router.post('/prices/latest/all')
async def post_all_latest_prices(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get latest prices for all known assets (POST version)"""
    return await get_all_latest_prices(_, assets_service)


class HistoricalPriceRequest(BaseModel):
    """Request model for historical price queries"""
    assets: list[str]
    target_asset: str = 'USD'
    from_timestamp: Timestamp
    to_timestamp: Timestamp


@router.get('/prices/historical')
async def get_historical_prices(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    asset: str,
    from_timestamp: Timestamp,
    to_timestamp: Timestamp,
    target_asset: str = 'USD',
) -> AssetResponse:
    """Get historical prices for an asset"""
    prices = assets_service.get_historical_prices(
        asset=asset,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        target_asset=target_asset,
    )
    
    return AssetResponse(result=prices)


@router.post('/prices/historical')
async def post_historical_prices(
    request_data: HistoricalPriceRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get historical prices for multiple assets"""
    results = {}
    
    for asset in request_data.assets:
        prices = assets_service.get_historical_prices(
            asset=asset,
            from_timestamp=request_data.from_timestamp,
            to_timestamp=request_data.to_timestamp,
            target_asset=request_data.target_asset,
        )
        results[asset] = prices
    
    return AssetResponse(result=results)


class AssetMappingRequest(BaseModel):
    """Request model for asset mappings"""
    asset: str
    target_asset: str
    mapping_type: str = 'price'  # 'price', 'location', 'counterparty'


@router.get('/mappings')
async def get_asset_mappings(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get all asset mappings"""
    mappings = assets_service.get_asset_mappings()
    
    return AssetResponse(result=mappings)


@router.post('/mappings')
async def modify_asset_mappings(
    mapping_data: AssetMappingRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Add or update asset mappings"""
    assets_service.set_asset_mapping(
        asset=mapping_data.asset,
        target_asset=mapping_data.target_asset,
        mapping_type=mapping_data.mapping_type,
    )
    
    return AssetResponse(
        result={'success': True},
        message='Asset mapping updated',
    )


@router.get('/updates')
async def check_asset_updates(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Check for asset database updates"""
    updates = assets_service.check_for_updates()
    
    return AssetResponse(result=updates)


@router.post('/updates')
async def apply_asset_updates(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Apply asset database updates"""
    result = assets_service.apply_updates()
    
    return AssetResponse(
        result=result,
        message='Asset updates applied',
    )
