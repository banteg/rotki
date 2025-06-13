"""Async Coingecko API client"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset, RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price
from rotki2.utils.async_http_client import AsyncHTTPClient

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset

logger = RotkehlchenLogsAdapter(__name__)

COINGECKO_API_URL = 'https://api.coingecko.com/api/v3'


class AsyncCoingecko:
    """Async version of Coingecko API client
    
    This is a simplified version focusing on price queries.
    A full implementation would include all Coingecko endpoints.
    """
    
    def __init__(self, http_client: AsyncHTTPClient | None = None):
        self.http_client = http_client or AsyncHTTPClient()
        self.api_key: str | None = None
        
    def set_api_key(self, api_key: str) -> None:
        """Set the API key for Coingecko Pro"""
        self.api_key = api_key
        
    def _get_headers(self) -> dict[str, str]:
        """Get headers including API key if available"""
        headers = {}
        if self.api_key:
            headers['x-cg-pro-api-key'] = self.api_key
        return headers
    
    async def query_current_price(
        self,
        from_asset: AssetWithOracles,
        to_asset: 'Asset',
    ) -> Price:
        """Query current price between two assets"""
        # Get Coingecko IDs
        from_id = from_asset.to_coingecko()
        to_id = to_asset.to_coingecko() if hasattr(to_asset, 'to_coingecko') else None
        
        if from_id is None:
            raise PriceQueryUnsupportedAsset(
                f'{from_asset.identifier} is not supported by Coingecko'
            )
        
        # Default to USD if to_asset doesn't have coingecko ID
        vs_currency = to_id or 'usd'
        
        try:
            url = f'{COINGECKO_API_URL}/simple/price'
            params = {
                'ids': from_id,
                'vs_currencies': vs_currency,
            }
            
            data = await self.http_client.get_json(
                url=url,
                params=params,
                headers=self._get_headers(),
            )
            
            if isinstance(data, dict) and from_id in data and vs_currency in data[from_id]:
                price = Price(data[from_id][vs_currency])
                logger.debug(f'Coingecko price for {from_id} vs {vs_currency}: {price}')
                return price
                
        except RemoteError as e:
            logger.warning(f'Failed to query Coingecko price: {e}')
            
        return ZERO_PRICE
    
    async def query_multiple_current_prices(
        self,
        assets: list[AssetWithOracles],
        to_asset: 'Asset',
    ) -> dict[AssetWithOracles, Price]:
        """Query current prices for multiple assets"""
        results = {}
        
        # Filter assets with coingecko IDs
        valid_assets = []
        asset_to_id = {}
        
        for asset in assets:
            cg_id = asset.to_coingecko()
            if cg_id:
                valid_assets.append(asset)
                asset_to_id[asset] = cg_id
        
        if not valid_assets:
            return results
        
        # Get target currency
        vs_currency = to_asset.to_coingecko() if hasattr(to_asset, 'to_coingecko') else 'usd'
        
        # Query in batches (Coingecko allows up to 250 IDs per request)
        batch_size = 250
        for i in range(0, len(valid_assets), batch_size):
            batch = valid_assets[i:i + batch_size]
            ids = [asset_to_id[asset] for asset in batch]
            
            try:
                url = f'{COINGECKO_API_URL}/simple/price'
                params = {
                    'ids': ','.join(ids),
                    'vs_currencies': vs_currency,
                }
                
                data = await self.http_client.get_json(
                    url=url,
                    params=params,
                    headers=self._get_headers(),
                )
                
                if isinstance(data, dict):
                    for asset in batch:
                        cg_id = asset_to_id[asset]
                        if cg_id in data and vs_currency in data[cg_id]:
                            results[asset] = Price(data[cg_id][vs_currency])
                        else:
                            results[asset] = ZERO_PRICE
                            
            except RemoteError as e:
                logger.warning(f'Failed to query Coingecko batch prices: {e}')
                # Set zero price for failed batch
                for asset in batch:
                    results[asset] = ZERO_PRICE
        
        return results
    
    async def query_historical_price(
        self,
        from_asset: AssetWithOracles,
        to_asset: 'Asset',
        timestamp: int,
    ) -> Price:
        """Query historical price at a specific timestamp"""
        from_id = from_asset.to_coingecko()
        if from_id is None:
            raise PriceQueryUnsupportedAsset(
                f'{from_asset.identifier} is not supported by Coingecko'
            )
        
        vs_currency = to_asset.to_coingecko() if hasattr(to_asset, 'to_coingecko') else 'usd'
        
        # Convert timestamp to date format (dd-mm-yyyy)
        from datetime import datetime
        date = datetime.fromtimestamp(timestamp)
        date_str = date.strftime('%d-%m-%Y')
        
        try:
            url = f'{COINGECKO_API_URL}/coins/{from_id}/history'
            params = {
                'date': date_str,
                'localization': 'false',
            }
            
            data = await self.http_client.get_json(
                url=url,
                params=params,
                headers=self._get_headers(),
            )
            
            if isinstance(data, dict) and 'market_data' in data:
                market_data = data['market_data']
                if 'current_price' in market_data and vs_currency in market_data['current_price']:
                    return Price(market_data['current_price'][vs_currency])
                    
        except RemoteError as e:
            logger.warning(f'Failed to query Coingecko historical price: {e}')
            
        return ZERO_PRICE
    
    async def close(self) -> None:
        """Close the HTTP client"""
        await self.http_client.close()