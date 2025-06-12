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
            symbol=asset_data.symbol,
            asset_type=asset_data.asset_type,
            decimals=asset_data.decimals,
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
