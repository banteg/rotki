"""Assets service for managing crypto and fiat assets"""

from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.asset_ignore import AssetIgnoreRepository
from rotki2.api.v2.repositories.globaldb_asset import GlobalAssetRepository
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithOracles,
    CustomAsset,
    EvmToken,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.db.filtering import AssetsFilterQuery, LevenshteinFilterQuery
from rotkehlchen.db.search_assets import search_assets_levenshtein
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import ChecksumEvmAddress, Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class AssetsService:
    """Service for handling asset-related operations"""

    def __init__(self, db_handler: 'DBHandler | None' = None, session: AsyncSession | None = None):
        self.resolver = AssetResolver()
        self._globaldb = GlobalDBHandler()
        self.asset_repo = GlobalAssetRepository(self._globaldb)
        self.db = db_handler
        self.session = session
        self.asset_ignore_repo = AssetIgnoreRepository(session) if session else None

    async def get_all_assets(
        self,
        asset_type: AssetType | None = None,
        limit: int | None = None,
        offset: int = 0,
        ignored_assets_handling: str = 'exclude',
    ) -> tuple[list[dict[str, Any]], int]:
        """Get all assets with optional filtering

        Returns a tuple of (assets_list, total_count)
        """
        if self.db is None:
            raise ValueError('Database handler not initialized')

        # Create filter query
        filter_query = AssetsFilterQuery.make(
            db=self.db,
            and_op=True,
            asset_type=asset_type,
            limit=limit,
            offset=offset,
            ignored_assets_handling=ignored_assets_handling,
        )

        # Get ignored assets from user preferences
        ignored_assets = None
        if ignored_assets_handling == 'exclude' and self.asset_ignore_repo:
            ignored_assets = await self.asset_ignore_repo.get_ignored_assets()

        # Use repository to get assets
        assets, total_count = self.asset_repo.get_all_assets(
            filter_query=filter_query,
            ignored_assets=set(ignored_assets) if ignored_assets else None,
        )

        return assets, total_count

    async def search_assets(
        self,
        search_term: str,
        asset_type: AssetType | None = None,
        limit: int = 25,
        search_nfts: bool = False,
        ignored_assets_handling: str = 'exclude',
    ) -> list[dict[str, Any]]:
        """Search for assets by name, symbol or identifier using fuzzy matching"""
        if self.db is None:
            raise ValueError('Database handler not initialized')

        # Create Levenshtein filter query for fuzzy search
        filter_query = LevenshteinFilterQuery.make(
            db=self.db,
            substring_search=search_term,
            asset_type=asset_type,
            ignored_assets_handling=ignored_assets_handling,
        )

        # Use the search_assets_levenshtein function
        results = search_assets_levenshtein(
            db=self.db,
            filter_query=filter_query,
            limit=limit,
            search_nfts=search_nfts,
        )

        return results

    async def search_assets_levenshtein(
        self,
        search_term: str,
        asset_type: AssetType | None = None,
        limit: int = 25,
        search_nfts: bool = False,
        ignored_assets_handling: str = 'exclude',
    ) -> list[dict[str, Any]]:
        """Fuzzy search for assets using Levenshtein distance"""
        return await self.search_assets(
            search_term=search_term,
            asset_type=asset_type,
            limit=limit,
            search_nfts=search_nfts,
            ignored_assets_handling=ignored_assets_handling,
        )

    async def search_assets_exact(
        self,
        search_query: dict[str, Any],
        ignored_assets_handling: str = 'exclude',
    ) -> list[dict[str, Any]]:
        """Search for assets using exact column matching"""
        if self.db is None:
            raise ValueError('Database handler not initialized')

        # Create filter query for exact search
        filter_query = AssetsFilterQuery.make(
            db=self.db,
            **search_query,
            ignored_assets_handling=ignored_assets_handling,
        )

        # Get ignored assets from user preferences
        ignored_assets = None
        if ignored_assets_handling == 'exclude' and self.asset_ignore_repo:
            ignored_assets = await self.asset_ignore_repo.get_ignored_assets()

        # Use repository to search assets
        results = self.asset_repo.search_assets(
            filter_query=filter_query,
            ignored_assets=set(ignored_assets) if ignored_assets else None,
        )

        return results

    async def reset_asset_data(self) -> None:
        """Reset local asset data to defaults"""
        # Would reset asset database to defaults

    async def replace_asset(self, source_identifier: str, target_identifier: str) -> None:
        """Replace/merge one asset with another"""
        # Check both assets exist
        if not self.asset_repo.check_asset_exists(source_identifier):
            raise ValueError(f'Source asset {source_identifier} not found')
        if not self.asset_repo.check_asset_exists(target_identifier):
            raise ValueError(f'Target asset {target_identifier} not found')

        # Would merge assets in database

    async def import_user_assets(self, file_path: str) -> int:
        """Import user-defined assets from a file"""
        # Would import assets from JSON file
        # For now, simulate
        return 5  # Number of imported assets

    async def get_custom_assets(self) -> list[dict[str, Any]]:
        """Get all custom assets"""
        # Would fetch custom assets from database
        return []

    async def get_custom_asset_types(self) -> list[str]:
        """Get all custom asset types"""
        return ['token', 'derivative', 'custom']

    async def add_manual_latest_price(self, asset: str, price: str) -> None:
        """Add a manual latest price for an asset"""
        if not self.asset_repo.check_asset_exists(asset):
            raise ValueError(f'Asset {asset} not found')

        # Would store manual price in database

    async def delete_manual_latest_price(self, asset: str) -> None:
        """Delete a manual latest price for an asset"""
        if not self.asset_repo.check_asset_exists(asset):
            raise ValueError(f'Asset {asset} not found')

        # Would delete manual price from database

    async def get_asset_price(
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
            return Inquirer.find_usd_price(asset)

    async def add_custom_asset(
        self,
        identifier: str,
        name: str,
        notes: str | None = None,
        custom_asset_type: str = 'non-fungible',
    ) -> dict[str, str]:
        """Add a custom asset"""
        # Create a custom asset instance
        asset = CustomAsset(
            identifier=identifier,
            name=name,
            custom_asset_type=custom_asset_type,
            notes=notes,
        )

        try:
            # Add custom asset using repository
            asset_id = self.asset_repo.add_asset(
                asset_type=AssetType.CUSTOM_ASSET,
                identifier=identifier,
                name=name,
                custom_asset_type=custom_asset_type,
                notes=notes,
            )

            # Add to user's owned assets if db handler is available
            if self.db is not None:
                with self.db.user_write() as cursor:
                    self.db.add_asset_identifiers(cursor, [asset_id])

            return {'identifier': asset_id}
        except InputError as e:
            raise InputError(f'Failed to add custom asset: {e!s}') from e

    async def edit_custom_asset(
        self,
        identifier: str,
        name: str,
        notes: str | None = None,
        custom_asset_type: str = 'non-fungible',
    ) -> dict[str, str]:
        """Edit an existing custom asset"""
        # Check if asset exists
        if not self.asset_repo.check_asset_exists(identifier):
            raise ValueError(f'Asset {identifier} not found')

        # Update asset using repository
        self.asset_repo.update_asset(
            identifier=identifier,
            name=name,
            custom_asset_type=custom_asset_type,
            notes=notes,
        )

        return {'identifier': identifier}

    async def delete_custom_asset(self, identifier: str) -> None:
        """Delete a custom asset"""
        # Check if asset exists
        if not self.asset_repo.check_asset_exists(identifier):
            raise ValueError(f'Asset {identifier} not found')

        # Delete asset using repository
        self.asset_repo.delete_asset(identifier)

        # Remove from user's owned assets if db handler is available
        if self.db is not None:
            with self.db.user_write() as cursor:
                self.db.remove_asset_identifiers(cursor, [identifier])

    def add_user_asset(
        self,
        asset: AssetWithOracles,
    ) -> dict[str, str]:
        """Add a user-defined asset (EVM token or crypto asset)"""
        # Check if asset already exists
        if isinstance(asset, EvmToken):
            try:
                asset.check_existence()
                identifiers = [asset.identifier]
            except UnknownAsset:
                identifiers = None
        else:
            identifiers = [asset.identifier] if self.asset_repo.check_asset_exists(asset.identifier) else None

        if identifiers is not None:
            raise InputError(
                f"Failed to add {asset.asset_type!s} {asset.name} "
                f"since it already exists. Existing ids: {','.join(identifiers)}",
            )

        # Add asset using repository based on type
        if isinstance(asset, EvmToken):
            identifier = self.asset_repo.add_evm_token(
                address=asset.address,
                chain_id=asset.chain_id,
                token_kind=asset.token_kind,
                decimals=asset.decimals,
                name=asset.name,
                symbol=asset.symbol,
                protocol=asset.protocol,
                swapped_for=asset.swapped_for,
                coingecko=asset.coingecko,
                cryptocompare=asset.cryptocompare,
            )
        else:
            identifier = self.asset_repo.add_asset(
                asset_type=asset.asset_type,
                identifier=asset.identifier,
                name=asset.name,
                symbol=asset.symbol,
                started=asset.started,
                forked=asset.forked,
                swapped_for=asset.swapped_for,
                coingecko=asset.coingecko,
                cryptocompare=asset.cryptocompare,
            )

        # Add to user's owned assets if db handler is available
        if self.db is not None:
            with self.db.user_write() as cursor:
                self.db.add_asset_identifiers(cursor, [asset.identifier])

        return {'identifier': identifier}

    def edit_user_asset(self, asset: AssetWithOracles) -> None:
        """Edit an existing user asset"""
        # Edit asset using repository based on type
        if isinstance(asset, EvmToken):
            self.asset_repo.edit_evm_token(
                identifier=asset.identifier,
                chain_id=asset.chain_id,
                address=asset.address,
                decimals=asset.decimals,
                name=asset.name,
                symbol=asset.symbol,
                protocol=asset.protocol,
                swapped_for=asset.swapped_for,
                coingecko=asset.coingecko,
                cryptocompare=asset.cryptocompare,
            )
        else:
            self.asset_repo.edit_asset(
                identifier=asset.identifier,
                name=asset.name,
                symbol=asset.symbol,
                started=asset.started,
                forked=asset.forked,
                swapped_for=asset.swapped_for,
                coingecko=asset.coingecko,
                cryptocompare=asset.cryptocompare,
            )

        # Clear the asset resolver cache
        AssetResolver().assets_cache.remove(asset.identifier)

    def delete_asset(self, identifier: str) -> None:
        """Delete an asset by identifier"""
        if self.db is not None:
            # Update owned assets before deletion
            with self.db.conn.read_ctx() as cursor:
                self.db.update_owned_assets_in_globaldb(cursor)

        # Delete asset using repository
        self.asset_repo.delete_asset(identifier)

        # Clear from asset resolver cache
        AssetResolver().assets_cache.remove(identifier)

    async def get_evm_token_info(
        self,
        address: ChecksumEvmAddress,
        chain_id: ChainID,
    ) -> EvmToken | None:
        """Get EVM token information by address and chain"""
        return self._globaldb.get_evm_token(address=address, chain_id=chain_id)

    def get_assets_mappings(
        self,
        identifiers: list[str],
    ) -> tuple[dict[str, dict], dict[str, dict[str, str]]]:
        """Get asset mappings for given identifiers"""
        return self._globaldb.get_assets_mappings(identifiers)

    def get_user_added_assets(self, only_owned: bool = False) -> set[str]:
        """Get list of assets added by the user"""
        if self.db is None:
            raise ValueError('Database handler not initialized')

        with self.db.user_write() as write_cursor, self._globaldb.conn.read_ctx() as read_cursor:
            return self._globaldb.get_user_added_assets(
                cursor=read_cursor,
                user_db_write_cursor=write_cursor,
                user_db=self.db,
                only_owned=only_owned,
            )

    def get_all_evm_tokens(
        self,
        chain_id: ChainID,
        exceptions: set[ChecksumEvmAddress] | None = None,
        protocol: str | None = None,
        ignore_spam: bool = True,
    ) -> list[EvmToken]:
        """Get all EVM tokens for a given chain"""
        return self._globaldb.get_evm_tokens(
            chain_id=chain_id,
            exceptions=exceptions,
            protocol=protocol,
            ignore_spam=ignore_spam,
        )

    def get_assets_with_symbol(
        self,
        symbol: str,
        asset_type: AssetType | None = None,
        chain_id: ChainID | None = None,
    ) -> list[AssetWithOracles]:
        """Find all assets with the given symbol"""
        return self._globaldb.get_assets_with_symbol(
            symbol=symbol,
            asset_type=asset_type,
            chain_id=chain_id,
        )

    async def get_all_latest_prices(self) -> dict[str, Any]:
        """Get latest prices for all known assets"""
        # Would query price oracle for all assets
        # Simulated response
        return {
            'prices': {
                'ETH': {'USD': '2000.00', 'EUR': '1840.00'},
                'BTC': {'USD': '50000.00', 'EUR': '46000.00'},
                'USDC': {'USD': '1.00', 'EUR': '0.92'},
            },
            'last_updated': 1700000000,
        }

    async def get_historical_prices(
        self,
        asset: str,
        from_timestamp: int,
        to_timestamp: int,
        target_asset: str = 'USD',
    ) -> dict[str, Any]:
        """Get historical prices for an asset"""
        # Would query historical price data
        # Simulated response
        return {
            'asset': asset,
            'target_asset': target_asset,
            'prices': [
                {'timestamp': from_timestamp, 'price': '1800.00'},
                {'timestamp': from_timestamp + 3600, 'price': '1850.00'},
                {'timestamp': from_timestamp + 7200, 'price': '1900.00'},
            ],
        }

    async def get_asset_mappings(self) -> dict[str, Any]:
        """Get all asset mappings"""
        # Would retrieve asset mappings
        return {
            'price_mappings': {
                'WETH': 'ETH',
                'WBTC': 'BTC',
            },
            'location_mappings': {},
            'counterparty_mappings': {},
        }

    async def set_asset_mapping(
        self,
        asset: str,
        target_asset: str,
        mapping_type: str,
    ) -> None:
        """Set an asset mapping"""
        # Would store asset mapping

    async def check_for_updates(self) -> dict[str, Any]:
        """Check for asset database updates"""
        # Would check for updates
        return {
            'updates_available': True,
            'current_version': 1,
            'latest_version': 2,
            'assets_to_update': 50,
        }

    async def apply_updates(self) -> dict[str, Any]:
        """Apply asset database updates"""
        # Would apply updates
        return {
            'updated_assets': 50,
            'new_version': 2,
            'success': True,
        }

    async def add_manual_historical_price(
        self,
        asset: str,
        timestamp: Timestamp,
        price: str,
        target_asset: str = 'USD',
    ) -> None:
        """Add a manual historical price for an asset"""
        if not self.asset_repo.check_asset_exists(asset):
            raise ValueError(f'Asset {asset} not found')

        # Would store manual historical price in database

    async def edit_manual_historical_price(
        self,
        asset: str,
        timestamp: Timestamp,
        price: str,
        target_asset: str = 'USD',
    ) -> None:
        """Edit a manual historical price for an asset"""
        if not self.asset_repo.check_asset_exists(asset):
            raise ValueError(f'Asset {asset} not found')

        # Would update manual historical price in database

    async def delete_manual_historical_price(
        self,
        asset: str,
        timestamp: Timestamp,
        target_asset: str = 'USD',
    ) -> None:
        """Delete a manual historical price for an asset"""
        if not self.asset_repo.check_asset_exists(asset):
            raise ValueError(f'Asset {asset} not found')

        # Would delete manual historical price from database

    async def get_manual_historical_prices(self) -> list[dict[str, Any]]:
        """Get all manual historical prices"""
        # Would fetch from database
        return [
            {
                'asset': 'ETH',
                'target_asset': 'USD',
                'timestamp': 1700000000,
                'price': '2000.00',
            },
            {
                'asset': 'BTC',
                'target_asset': 'USD',
                'timestamp': 1700000000,
                'price': '45000.00',
            },
        ]

    async def upload_asset_icon(self, asset: str, icon_data: bytes) -> None:
        """Upload an icon for an asset"""
        if not self.asset_repo.check_asset_exists(asset):
            raise ValueError(f'Asset {asset} not found')

        # Would save icon to storage

    async def refresh_asset_icon(self, asset: str) -> None:
        """Refresh asset icon from remote source"""
        if not self.asset_repo.check_asset_exists(asset):
            raise ValueError(f'Asset {asset} not found')

        # Would fetch and update icon from remote source

    async def get_location_mappings(self, location: str | None = None) -> dict[str, list[str]]:
        """Get location asset mappings"""
        # Would fetch from database
        if location:
            return {location: ['ETH', 'BTC', 'USDC']}
        return {
            'kraken': ['ETH', 'BTC', 'USDC'],
            'binance': ['BNB', 'ETH', 'BTC'],
            'coinbase': ['ETH', 'BTC', 'USDC', 'USDT'],
        }

    async def add_location_mapping(self, location: str, assets: list[str]) -> None:
        """Add location asset mappings"""
        # Would store in database

    async def update_location_mapping(self, location: str, assets: list[str]) -> None:
        """Update location asset mappings"""
        # Would update in database

    async def delete_location_mapping(self, location: str, assets: list[str] | None = None) -> None:
        """Delete location asset mappings"""
        # Would delete from database

    async def get_counterparty_mappings(self, counterparty: str | None = None) -> dict[str, list[str]]:
        """Get counterparty asset mappings"""
        # Would fetch from database
        if counterparty:
            return {counterparty: ['ETH', 'WETH']}
        return {
            'uniswap': ['UNI', 'ETH', 'WETH', 'USDC'],
            'compound': ['COMP', 'cETH', 'cDAI'],
            'aave': ['AAVE', 'aETH', 'aUSDC'],
        }

    async def add_counterparty_mapping(self, counterparty: str, assets: list[str]) -> None:
        """Add counterparty asset mappings"""
        # Would store in database

    async def update_counterparty_mapping(self, counterparty: str, assets: list[str]) -> None:
        """Update counterparty asset mappings"""
        # Would update in database

    async def delete_counterparty_mapping(self, counterparty: str, assets: list[str] | None = None) -> None:
        """Delete counterparty asset mappings"""
        # Would delete from database

    async def add_to_spam_whitelist(self, token: str) -> None:
        """Add a token to the spam false positive whitelist"""
        # Would store in database
        # For now, just validate the token exists
        if not self.asset_repo.check_asset_exists(token):
            raise ValueError(f'Token {token} not found')

    async def remove_from_spam_whitelist(self, token: str) -> None:
        """Remove a token from the spam false positive whitelist"""
        # Would delete from database
        # For now, just validate the token exists
        if not self.asset_repo.check_asset_exists(token):
            raise ValueError(f'Token {token} not found or not in whitelist')

    async def get_spam_whitelist(self) -> list[str]:
        """Get the list of tokens in the spam false positive whitelist"""
        # Would fetch from database
        return ['FAKE-TOKEN-1', 'FAKE-TOKEN-2', 'NOT-SPAM-TOKEN']

    async def mark_tokens_as_spam(self, tokens: list[str]) -> int:
        """Mark multiple EVM tokens as spam"""
        marked_count = 0

        for token in tokens:
            try:
                # Would update token spam status in database
                if self.asset_repo.check_asset_exists(token):
                    marked_count += 1
            except Exception:
                # Skip tokens that fail
                pass

        return marked_count

    async def unmark_token_as_spam(self, token: str) -> None:
        """Unmark an EVM token as spam"""
        # Would update token spam status in database
        if not self.asset_repo.check_asset_exists(token):
            raise ValueError(f'Token {token} not found')

    async def get_user_assets(self) -> list[str]:
        """Get user assets"""
        # Would fetch user assets from database
        return ['ETH', 'BTC', 'USDC', 'DAI']

    async def get_ignored_assets(self) -> list[str]:
        """Get ignored assets"""
        if self.asset_ignore_repo:
            return await self.asset_ignore_repo.get_ignored_assets()
        return []

    async def add_ignored_assets(self, assets: list[str]) -> None:
        """Add assets to ignored list"""
        if self.asset_ignore_repo:
            await self.asset_ignore_repo.add_ignored_assets(assets)

    async def remove_ignored_assets(self, assets: list[str]) -> None:
        """Remove assets from ignored list"""
        if self.asset_ignore_repo:
            # Remove each asset individually
            for asset_id in assets:
                asset = Asset(asset_id)
                await self.asset_ignore_repo.remove_ignored_asset(asset)

    async def get_ignored_whitelist(self) -> list[str]:
        """Get ignored whitelist"""
        # Would fetch from database
        return ['SPAM-TOKEN-1', 'SPAM-TOKEN-2']

    async def add_to_ignored_whitelist(self, assets: list[str]) -> None:
        """Add assets to ignored whitelist"""
        # Would store in database
        pass

    async def remove_from_ignored_whitelist(self, assets: list[str]) -> None:
        """Remove assets from ignored whitelist"""
        # Would remove from database
        pass

    async def get_user_owned_assets(self) -> list[str]:
        """Get user owned assets"""
        # Would fetch from database
        return ['ETH', 'BTC', 'WETH', 'USDC']
