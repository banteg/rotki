"""Async Defillama API client"""
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

DEFILLAMA_API_URL = 'https://coins.llama.fi'


class AsyncDefillama:
    """Async version of Defillama API client"""
    
    def __init__(self, http_client: AsyncHTTPClient | None = None):
        self.http_client = http_client or AsyncHTTPClient()
        
    async def query_current_price(
        self,
        from_asset: AssetWithOracles,
        to_asset: 'Asset',
    ) -> Price:
        """Query current price between two assets"""
        # Defillama uses chain:address format for tokens
        identifier = self._get_defillama_identifier(from_asset)
        if identifier is None:
            raise PriceQueryUnsupportedAsset(
                f'{from_asset.identifier} is not supported by Defillama'
            )
        
        # Defillama only supports USD prices
        if hasattr(to_asset, 'identifier') and to_asset.identifier != 'USD':
            logger.debug(f'Defillama only supports USD prices, not {to_asset.identifier}')
            return ZERO_PRICE
        
        try:
            url = f'{DEFILLAMA_API_URL}/prices/current/{identifier}'
            
            data = await self.http_client.get_json(url=url)
            
            if isinstance(data, dict) and 'coins' in data and identifier in data['coins']:
                coin_data = data['coins'][identifier]
                if 'price' in coin_data:
                    price = Price(coin_data['price'])
                    logger.debug(f'Defillama price for {identifier}: {price}')
                    return price
                    
        except RemoteError as e:
            logger.warning(f'Failed to query Defillama price: {e}')
            
        return ZERO_PRICE
    
    async def query_multiple_current_prices(
        self,
        assets: list[AssetWithOracles],
        to_asset: 'Asset',
    ) -> dict[AssetWithOracles, Price]:
        """Query current prices for multiple assets"""
        results = {}
        
        # Defillama only supports USD prices
        if hasattr(to_asset, 'identifier') and to_asset.identifier != 'USD':
            logger.debug(f'Defillama only supports USD prices, not {to_asset.identifier}')
            return {asset: ZERO_PRICE for asset in assets}
        
        # Get valid identifiers
        valid_assets = []
        identifiers = []
        
        for asset in assets:
            identifier = self._get_defillama_identifier(asset)
            if identifier:
                valid_assets.append(asset)
                identifiers.append(identifier)
        
        if not valid_assets:
            return results
        
        # Query in batches
        batch_size = 50
        for i in range(0, len(valid_assets), batch_size):
            batch_assets = valid_assets[i:i + batch_size]
            batch_ids = identifiers[i:i + batch_size]
            
            try:
                # Defillama accepts comma-separated identifiers
                ids_str = ','.join(batch_ids)
                url = f'{DEFILLAMA_API_URL}/prices/current/{ids_str}'
                
                data = await self.http_client.get_json(url=url)
                
                if isinstance(data, dict) and 'coins' in data:
                    for asset, identifier in zip(batch_assets, batch_ids):
                        if identifier in data['coins'] and 'price' in data['coins'][identifier]:
                            results[asset] = Price(data['coins'][identifier]['price'])
                        else:
                            results[asset] = ZERO_PRICE
                            
            except RemoteError as e:
                logger.warning(f'Failed to query Defillama batch prices: {e}')
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
        identifier = self._get_defillama_identifier(from_asset)
        if identifier is None:
            raise PriceQueryUnsupportedAsset(
                f'{from_asset.identifier} is not supported by Defillama'
            )
        
        # Defillama only supports USD prices
        if hasattr(to_asset, 'identifier') and to_asset.identifier != 'USD':
            return ZERO_PRICE
        
        try:
            url = f'{DEFILLAMA_API_URL}/prices/historical/{timestamp}/{identifier}'
            
            data = await self.http_client.get_json(url=url)
            
            if isinstance(data, dict) and 'coins' in data and identifier in data['coins']:
                coin_data = data['coins'][identifier]
                if 'price' in coin_data:
                    return Price(coin_data['price'])
                    
        except RemoteError as e:
            logger.warning(f'Failed to query Defillama historical price: {e}')
            
        return ZERO_PRICE
    
    def _get_defillama_identifier(self, asset: AssetWithOracles) -> str | None:
        """Get Defillama identifier for an asset
        
        Defillama uses chain:address format for tokens
        """
        # Check if asset has a direct defillama mapping
        if hasattr(asset, 'to_defillama'):
            return asset.to_defillama()
        
        # For EVM tokens, construct the identifier
        if hasattr(asset, 'chain_id') and hasattr(asset, 'address'):
            chain_map = {
                1: 'ethereum',
                10: 'optimism', 
                56: 'bsc',
                100: 'gnosis',
                137: 'polygon',
                250: 'fantom',
                42161: 'arbitrum',
                43114: 'avalanche',
            }
            
            chain = chain_map.get(asset.chain_id)
            if chain:
                return f'{chain}:{asset.address}'
        
        return None
    
    async def close(self) -> None:
        """Close the HTTP client"""
        await self.http_client.close()