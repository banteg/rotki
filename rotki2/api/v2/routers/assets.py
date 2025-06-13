"""Assets router for asset management endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.assets import AssetsService
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
            notes=f'Symbol: {asset_data.symbol}',
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
            notes=f'Symbol: {asset_data.symbol}',
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


# Additional endpoints for full v1 compatibility

@router.post('/search')
async def search_assets_post(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    search_term: str,
    asset_type: AssetType | None = None,
    limit: int = 25,
) -> AssetResponse:
    """Search for assets by name or symbol - Compatible with v1 POST /api/1/assets/search"""
    return await search_assets(_, assets_service, search_term, asset_type, limit)


@router.post('/search/levenshtein')
async def search_assets_fuzzy(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    search_term: str,
    asset_type: AssetType | None = None,
    limit: int = 25,
    search_nfts: bool = False,
    ignored_assets_handling: str = 'exclude',
) -> AssetResponse:
    """Fuzzy search for assets - Compatible with v1 POST /api/1/assets/search/levenshtein"""
    results = assets_service.search_assets_levenshtein(
        search_term=search_term,
        asset_type=asset_type,
        limit=limit,
        search_nfts=search_nfts,
        ignored_assets_handling=ignored_assets_handling,
    )

    return AssetResponse(
        result={
            'assets': results,
            'total': len(results),
        },
    )


@router.put('/replace')
async def replace_asset(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    source_identifier: str,
    target_identifier: str,
) -> AssetResponse:
    """Replace/merge one asset with another - Compatible with v1 PUT /api/1/assets/replace"""
    try:
        assets_service.replace_asset(source_identifier, target_identifier)

        return AssetResponse(
            result={'success': True},
            message=f'Successfully replaced {source_identifier} with {target_identifier}',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/updates')
async def reset_asset_data(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Reset local asset data to defaults - Compatible with v1 DELETE /api/1/assets/updates"""
    assets_service.reset_asset_data()

    return AssetResponse(
        result={'success': True},
        message='Asset data reset to defaults',
    )


@router.put('/user')
async def import_user_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    file_path: str,
) -> AssetResponse:
    """Import user-defined assets from a file - Compatible with v1 PUT /api/1/assets/user"""
    try:
        count = assets_service.import_user_assets(file_path)

        return AssetResponse(
            result={'imported': count},
            message=f'Successfully imported {count} assets',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get('/custom')
async def get_custom_assets(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get all custom assets - Compatible with v1 GET /api/1/assets/custom"""
    custom_assets = assets_service.get_custom_assets()

    return AssetResponse(result={'assets': custom_assets})


@router.put('/custom')
async def add_custom_asset_v1(
    asset_data: CustomAssetRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Add a new custom asset - Compatible with v1 PUT /api/1/assets/custom"""
    return await add_custom_asset(asset_data, _, assets_service)


@router.patch('/custom')
async def edit_custom_asset_v1(
    asset_data: CustomAssetRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Edit a custom asset - Compatible with v1 PATCH /api/1/assets/custom"""
    return await edit_custom_asset(asset_data, _, assets_service)


@router.delete('/custom')
async def delete_custom_asset_v1(
    identifier: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Delete a custom asset - Compatible with v1 DELETE /api/1/assets/custom"""
    return await delete_custom_asset(identifier, _, assets_service)


@router.get('/custom/types')
async def get_custom_asset_types(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get all custom asset types - Compatible with v1 GET /api/1/assets/custom/types"""
    types = assets_service.get_custom_asset_types()

    return AssetResponse(result={'types': types})


@router.put('/prices/latest')
async def add_manual_latest_price(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    asset: str,
    price: str,
) -> AssetResponse:
    """Add a manual latest price - Compatible with v1 PUT /api/1/assets/prices/latest"""
    try:
        assets_service.add_manual_latest_price(asset, price)

        return AssetResponse(
            result={'success': True},
            message='Manual latest price added',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/prices/latest')
async def delete_manual_latest_price(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    asset: str,
) -> AssetResponse:
    """Delete a manual latest price - Compatible with v1 DELETE /api/1/assets/prices/latest"""
    try:
        assets_service.delete_manual_latest_price(asset)

        return AssetResponse(
            result={'success': True},
            message='Manual latest price deleted',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get('/prices/historical/manual')
async def get_manual_historical_prices(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get all stored manual historical prices - Compatible with v1 GET /api/1/assets/prices/historical"""
    prices = assets_service.get_manual_historical_prices()

    return AssetResponse(result={'prices': prices})


@router.put('/prices/historical')
async def add_manual_historical_price(
    asset: str,
    timestamp: Timestamp,
    price: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    target_asset: str = 'USD',
) -> AssetResponse:
    """Add a manual historical price - Compatible with v1 PUT /api/1/assets/prices/historical"""
    try:
        assets_service.add_manual_historical_price(asset, timestamp, price, target_asset)

        return AssetResponse(
            result={'success': True},
            message='Manual historical price added',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch('/prices/historical')
async def edit_manual_historical_price(
    asset: str,
    timestamp: Timestamp,
    price: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    target_asset: str = 'USD',
) -> AssetResponse:
    """Edit a manual historical price - Compatible with v1 PATCH /api/1/assets/prices/historical"""
    try:
        assets_service.edit_manual_historical_price(asset, timestamp, price, target_asset)

        return AssetResponse(
            result={'success': True},
            message='Manual historical price updated',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/prices/historical')
async def delete_manual_historical_price(
    asset: str,
    timestamp: Timestamp,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    target_asset: str = 'USD',
) -> AssetResponse:
    """Delete a manual historical price - Compatible with v1 DELETE /api/1/assets/prices/historical"""
    try:
        assets_service.delete_manual_historical_price(asset, timestamp, target_asset)

        return AssetResponse(
            result={'success': True},
            message='Manual historical price deleted',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# Asset icon endpoints
@router.put('/icon/modify')
async def upload_asset_icon(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    asset: str = Form(...),
    file: UploadFile = File(...),
) -> AssetResponse:
    """Upload an asset icon - Compatible with v1 PUT /api/1/assets/icon/modify"""
    try:
        # Read file content
        icon_data = await file.read()
        assets_service.upload_asset_icon(asset, icon_data)

        return AssetResponse(
            result={'success': True},
            message=f'Icon uploaded for asset {asset}',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post('/icon/modify')
async def upload_asset_icon_via_form(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    asset: str = Form(...),
    file: UploadFile = File(...),
) -> AssetResponse:
    """Upload an asset icon via form - Compatible with v1 POST /api/1/assets/icon/modify"""
    return await upload_asset_icon(_, assets_service, asset, file)


@router.patch('/icon/modify')
async def refresh_asset_icon(
    asset: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Refresh an asset icon from remote source - Compatible with v1 PATCH /api/1/assets/icon/modify"""
    try:
        assets_service.refresh_asset_icon(asset)

        return AssetResponse(
            result={'success': True},
            message=f'Icon refreshed for asset {asset}',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Location mappings endpoints
@router.post('/locationmappings')
async def query_location_mappings(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    location: str | None = None,
) -> AssetResponse:
    """Query location asset mappings - Compatible with v1 POST /api/1/assets/locationmappings"""
    mappings = assets_service.get_location_mappings(location)

    return AssetResponse(result={'mappings': mappings})


@router.put('/locationmappings')
async def add_location_mappings(
    location: str,
    assets: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Add location asset mappings - Compatible with v1 PUT /api/1/assets/locationmappings"""
    try:
        assets_service.add_location_mapping(location, assets)

        return AssetResponse(
            result={'success': True},
            message=f'Added {len(assets)} asset mappings for location {location}',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch('/locationmappings')
async def update_location_mappings(
    location: str,
    assets: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Update location asset mappings - Compatible with v1 PATCH /api/1/assets/locationmappings"""
    try:
        assets_service.update_location_mapping(location, assets)

        return AssetResponse(
            result={'success': True},
            message=f'Updated asset mappings for location {location}',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/locationmappings')
async def delete_location_mappings(
    location: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    assets: list[str] | None = None,
) -> AssetResponse:
    """Delete location asset mappings - Compatible with v1 DELETE /api/1/assets/locationmappings"""
    try:
        assets_service.delete_location_mapping(location, assets)

        return AssetResponse(
            result={'success': True},
            message=f'Deleted asset mappings for location {location}',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Counterparty mappings endpoints
@router.post('/counterpartymappings')
async def query_counterparty_mappings(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    counterparty: str | None = None,
) -> AssetResponse:
    """Query counterparty asset mappings - Compatible with v1 POST /api/1/assets/counterpartymappings"""
    mappings = assets_service.get_counterparty_mappings(counterparty)

    return AssetResponse(result={'mappings': mappings})


@router.put('/counterpartymappings')
async def add_counterparty_mappings(
    counterparty: str,
    assets: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Add counterparty asset mappings - Compatible with v1 PUT /api/1/assets/counterpartymappings"""
    try:
        assets_service.add_counterparty_mapping(counterparty, assets)

        return AssetResponse(
            result={'success': True},
            message=f'Added {len(assets)} asset mappings for counterparty {counterparty}',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch('/counterpartymappings')
async def update_counterparty_mappings(
    counterparty: str,
    assets: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Update counterparty asset mappings - Compatible with v1 PATCH /api/1/assets/counterpartymappings"""
    try:
        assets_service.update_counterparty_mapping(counterparty, assets)

        return AssetResponse(
            result={'success': True},
            message=f'Updated asset mappings for counterparty {counterparty}',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/counterpartymappings')
async def delete_counterparty_mappings(
    counterparty: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
    assets: list[str] | None = None,
) -> AssetResponse:
    """Delete counterparty asset mappings - Compatible with v1 DELETE /api/1/assets/counterpartymappings"""
    try:
        assets_service.delete_counterparty_mapping(counterparty, assets)

        return AssetResponse(
            result={'success': True},
            message=f'Deleted asset mappings for counterparty {counterparty}',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Spam token and whitelist endpoints
@router.post('/ignored/whitelist')
async def add_to_spam_whitelist(
    token: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Add a spam token to the false positive list - Compatible with v1 POST /api/1/assets/ignored/whitelist"""
    try:
        assets_service.add_to_spam_whitelist(token)

        return AssetResponse(
            result={'success': True},
            message=f'Token {token} added to whitelist',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/ignored/whitelist')
async def remove_from_spam_whitelist(
    token: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Remove a token from the false positive list - Compatible with v1 DELETE /api/1/assets/ignored/whitelist"""
    try:
        assets_service.remove_from_spam_whitelist(token)

        return AssetResponse(
            result={'success': True},
            message=f'Token {token} removed from whitelist',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get('/ignored/whitelist')
async def get_spam_whitelist(
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Get the list of false positive spam tokens - Compatible with v1 GET /api/1/assets/ignored/whitelist"""
    whitelist = assets_service.get_spam_whitelist()

    return AssetResponse(result={'tokens': whitelist})


@router.post('/evm/spam')
async def mark_tokens_as_spam(
    tokens: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Mark EVM tokens as spam - Compatible with v1 POST /api/1/assets/evm/spam/"""
    try:
        marked_count = assets_service.mark_tokens_as_spam(tokens)

        return AssetResponse(
            result={'marked': marked_count},
            message=f'Marked {marked_count} tokens as spam',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/evm/spam')
async def unmark_token_as_spam(
    token: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets_service: Annotated[AssetsService, Depends(get_assets_service)],
) -> AssetResponse:
    """Unmark an EVM token as spam - Compatible with v1 DELETE /api/1/assets/evm/spam/"""
    try:
        assets_service.unmark_token_as_spam(token)

        return AssetResponse(
            result={'success': True},
            message=f'Token {token} unmarked as spam',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
