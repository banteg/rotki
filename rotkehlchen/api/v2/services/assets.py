"""Assets service for managing crypto and fiat assets"""

from rotkehlchen.assets.asset import Asset, AssetWithNameAndType, EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.types import Price, Timestamp


class AssetsService:
    """Service for handling asset-related operations"""

    def __init__(self):
        self.resolver = AssetResolver()
        self.globaldb = GlobalDBHandler()

    def get_all_assets(
        self,
        asset_type: AssetType | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[AssetWithNameAndType]:
        """Get all assets with optional filtering"""
        # In real implementation, would query from globaldb with filters
        assets = []

        # This is a simplified version
        with self.globaldb.conn.read_ctx() as cursor:
            query = 'SELECT identifier, name, symbol FROM assets'
            params = []

            if asset_type:
                query += ' WHERE type = ?'
                params.append(asset_type.value)

            if limit:
                query += f' LIMIT {limit} OFFSET {offset}'

            cursor.execute(query, params)

            for row in cursor:
                assets.append(AssetWithNameAndType(
                    identifier=row[0],
                    name=row[1],
                    symbol=row[2],
                    asset_type=asset_type or AssetType.OWN_CHAIN,
                ))

        return assets

    def search_assets(
        self,
        search_term: str,
        asset_type: AssetType | None = None,
        limit: int = 25,
    ) -> list[Asset]:
        """Search for assets by name or symbol"""
        # Simplified search implementation
        results = []
        search_lower = search_term.lower()

        all_assets = self.get_all_assets(asset_type=asset_type, limit=limit)

        for asset in all_assets:
            if (search_lower in asset.name.lower() or
                search_lower in asset.symbol.lower() or
                search_lower in asset.identifier.lower()):
                results.append(Asset(asset.identifier))

        return results[:limit]

    def get_asset_price(
        self,
        asset: Asset,
        target_asset: Asset = A_USD,
        timestamp: Timestamp | None = None,
    ) -> Price:
        """Get asset price at given timestamp"""
        if timestamp:
            return PriceHistorian.query_historical_price(
                from_asset=asset,
                to_asset=target_asset,
                timestamp=timestamp,
            )
        else:
            # Get current price
            return PriceHistorian.query_current_price(
                from_asset=asset,
                to_asset=target_asset,
            )

    def add_custom_asset(
        self,
        identifier: str,
        name: str,
        symbol: str,
        asset_type: AssetType,
        decimals: int | None = None,
    ) -> Asset:
        """Add a custom asset"""
        # In real implementation, would add to custom assets table
        return Asset(identifier)

    def get_evm_token_info(self, address: str, chain_id: int) -> EvmToken | None:
        """Get EVM token information"""
        try:
            token = EvmToken(f'eip155:{chain_id}/erc20:{address}')
            return token
        except UnknownAsset:
            return None
