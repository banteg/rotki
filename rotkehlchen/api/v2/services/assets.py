"""Assets service for managing crypto and fiat assets"""

from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
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

    def __init__(self, db_handler: 'DBHandler | None' = None):
        self.resolver = AssetResolver()
        self.globaldb = GlobalDBHandler()
        self.db = db_handler

    def get_all_assets(
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

        # Use the GlobalDBHandler's retrieve_assets method
        assets, total_count = GlobalDBHandler.retrieve_assets(
            userdb=self.db,
            filter_query=filter_query,
        )

        return assets, total_count

    def search_assets(
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

    def search_assets_exact(
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

        # Use the GlobalDBHandler's search_assets method
        results = GlobalDBHandler.search_assets(
            filter_query=filter_query,
            db=self.db,
        )

        return results

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
            return Inquirer.find_usd_price(asset)

    def add_custom_asset(
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
            # Add to global database
            GlobalDBHandler.add_asset(asset)

            # Add to user's owned assets if db handler is available
            if self.db is not None:
                with self.db.user_write() as cursor:
                    self.db.add_asset_identifiers(cursor, [identifier])

            return {'identifier': identifier}
        except InputError as e:
            raise InputError(f'Failed to add custom asset: {str(e)}') from e
    
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
            identifiers = GlobalDBHandler.check_asset_exists(asset)
        
        if identifiers is not None:
            raise InputError(
                f"Failed to add {asset.asset_type!s} {asset.name} "
                f"since it already exists. Existing ids: {','.join(identifiers)}"
            )
        
        # Add to global database
        GlobalDBHandler.add_asset(asset)

        # Add to user's owned assets if db handler is available
        if self.db is not None:
            with self.db.user_write() as cursor:
                self.db.add_asset_identifiers(cursor, [asset.identifier])

        return {'identifier': asset.identifier}
    
    def edit_user_asset(self, asset: AssetWithOracles) -> None:
        """Edit an existing user asset"""
        GlobalDBHandler.edit_user_asset(asset)

        # Clear the asset resolver cache
        AssetResolver().assets_cache.remove(asset.identifier)

    def delete_asset(self, identifier: str) -> None:
        """Delete an asset by identifier"""
        if self.db is not None:
            # Update owned assets before deletion
            with self.db.conn.read_ctx() as cursor:
                self.db.update_owned_assets_in_globaldb(cursor)

        # Delete from global database
        GlobalDBHandler.delete_asset_by_identifier(identifier)

        # Clear from asset resolver cache
        AssetResolver().assets_cache.remove(identifier)

    def get_evm_token_info(
        self,
        address: ChecksumEvmAddress,
        chain_id: ChainID,
    ) -> EvmToken | None:
        """Get EVM token information by address and chain"""
        return GlobalDBHandler.get_evm_token(address=address, chain_id=chain_id)
    
    def get_assets_mappings(
        self,
        identifiers: list[str],
    ) -> tuple[dict[str, dict], dict[str, dict[str, str]]]:
        """Get asset mappings for given identifiers"""
        return GlobalDBHandler.get_assets_mappings(identifiers)

    def get_user_added_assets(self, only_owned: bool = False) -> set[str]:
        """Get list of assets added by the user"""
        if self.db is None:
            raise ValueError('Database handler not initialized')

        with self.db.user_write() as write_cursor, self.globaldb.conn.read_ctx() as read_cursor:
            return GlobalDBHandler.get_user_added_assets(
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
        return GlobalDBHandler.get_evm_tokens(
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
        return GlobalDBHandler.get_assets_with_symbol(
            symbol=symbol,
            asset_type=asset_type,
            chain_id=chain_id,
        )
