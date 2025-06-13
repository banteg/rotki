"""Async Cryptocompare API client"""
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

CRYPTOCOMPARE_API_URL = 'https://min-api.cryptocompare.com/data'


class AsyncCryptocompare:
    """Async version of Cryptocompare API client"""
    
    def __init__(self, http_client: AsyncHTTPClient | None = None):
        self.http_client = http_client or AsyncHTTPClient()
        self.api_key: str | None = None
        
    def set_api_key(self, api_key: str) -> None:
        """Set the API key for Cryptocompare"""
        self.api_key = api_key
        
    def _get_headers(self) -> dict[str, str]:
        """Get headers including API key if available"""
        headers = {}
        if self.api_key:
            headers['authorization'] = f'Apikey {self.api_key}'
        return headers
    
    async def query_current_price(
        self,
        from_asset: AssetWithOracles,
        to_asset: 'Asset',
    ) -> Price:
        """Query current price between two assets"""
        # Get Cryptocompare symbols
        from_symbol = from_asset.to_cryptocompare()
        to_symbol = to_asset.to_cryptocompare() if hasattr(to_asset, 'to_cryptocompare') else 'USD'
        
        if from_symbol is None:
            raise PriceQueryUnsupportedAsset(
                f'{from_asset.identifier} is not supported by Cryptocompare'
            )
        
        try:
            url = f'{CRYPTOCOMPARE_API_URL}/price'
            params = {
                'fsym': from_symbol,
                'tsyms': to_symbol,
            }
            
            data = await self.http_client.get_json(
                url=url,
                params=params,
                headers=self._get_headers(),
            )
            
            if isinstance(data, dict) and to_symbol in data:
                price = Price(data[to_symbol])
                logger.debug(f'Cryptocompare price for {from_symbol} vs {to_symbol}: {price}')
                return price
                
        except RemoteError as e:
            logger.warning(f'Failed to query Cryptocompare price: {e}')
            
        return ZERO_PRICE
    
    async def query_multiple_current_prices(
        self,
        assets: list[AssetWithOracles],
        to_asset: 'Asset',
    ) -> dict[AssetWithOracles, Price]:
        """Query current prices for multiple assets"""
        results = {}
        
        # Get target symbol
        to_symbol = to_asset.to_cryptocompare() if hasattr(to_asset, 'to_cryptocompare') else 'USD'
        
        # Cryptocompare allows multiple fsyms in one request
        valid_assets = []
        symbols = []
        
        for asset in assets:
            symbol = asset.to_cryptocompare()
            if symbol:
                valid_assets.append(asset)
                symbols.append(symbol)
        
        if not valid_assets:
            return results
        
        # Query in batches (limit symbols per request)
        batch_size = 50
        for i in range(0, len(valid_assets), batch_size):
            batch_assets = valid_assets[i:i + batch_size]
            batch_symbols = symbols[i:i + batch_size]
            
            try:
                url = f'{CRYPTOCOMPARE_API_URL}/pricemulti'
                params = {
                    'fsyms': ','.join(batch_symbols),
                    'tsyms': to_symbol,
                }
                
                data = await self.http_client.get_json(
                    url=url,
                    params=params,
                    headers=self._get_headers(),
                )
                
                if isinstance(data, dict):
                    for asset, symbol in zip(batch_assets, batch_symbols):
                        if symbol in data and to_symbol in data[symbol]:
                            results[asset] = Price(data[symbol][to_symbol])
                        else:
                            results[asset] = ZERO_PRICE
                            
            except RemoteError as e:
                logger.warning(f'Failed to query Cryptocompare batch prices: {e}')
                # Set zero price for failed batch
                for asset in batch_assets:
                    results[asset] = ZERO_PRICE
        
        return results
    
    async def query_historical_price(
        self,
        from_asset: AssetWithOracles,
        to_asset: 'Asset',
        timestamp: int,
    ) -> Price:
        """Query historical price at a specific timestamp"""
        from_symbol = from_asset.to_cryptocompare()
        if from_symbol is None:
            raise PriceQueryUnsupportedAsset(
                f'{from_asset.identifier} is not supported by Cryptocompare'
            )
        
        to_symbol = to_asset.to_cryptocompare() if hasattr(to_asset, 'to_cryptocompare') else 'USD'
        
        try:
            url = f'{CRYPTOCOMPARE_API_URL}/pricehistorical'
            params = {
                'fsym': from_symbol,
                'tsyms': to_symbol,
                'ts': timestamp,
            }
            
            data = await self.http_client.get_json(
                url=url,
                params=params,
                headers=self._get_headers(),
            )
            
            if isinstance(data, dict) and from_symbol in data and to_symbol in data[from_symbol]:
                return Price(data[from_symbol][to_symbol])
                
        except RemoteError as e:
            logger.warning(f'Failed to query Cryptocompare historical price: {e}')
            
        return ZERO_PRICE
    
    async def close(self) -> None:
        """Close the HTTP client"""
        await self.http_client.close()