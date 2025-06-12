"""Global database asset repository for v2 API.

This repository wraps GlobalDBHandler functionality for asset operations.
"""
from typing import Any, Optional

from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.db.filtering import AssetsFilterQuery
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import ChecksumEvmAddress


class GlobalAssetRepository:
    """Repository for global asset database operations.
    
    This wraps the GlobalDBHandler to provide a clean interface for the service layer.
    """
    
    def __init__(self, globaldb: GlobalDBHandler):
        self.globaldb = globaldb
    
    def get_all_assets(
        self,
        filter_query: Optional[AssetsFilterQuery] = None,
        ignored_assets: Optional[set[str]] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get all assets with filtering and pagination.
        
        Returns:
            Tuple of (asset list, total count)
        """
        if filter_query is None:
            filter_query = AssetsFilterQuery.make()
        
        # Delegate to GlobalDBHandler's retrieve_assets method
        return self.globaldb.retrieve_assets(
            filter_query=filter_query,
            ignored_assets_handling='exclude' if ignored_assets else 'none',
            ignored_asset_ids=ignored_assets,
        )
    
    def get_asset_by_identifier(self, identifier: str) -> Optional[AssetWithOracles]:
        """Get a single asset by its identifier."""
        return self.globaldb.get_asset_data(identifier=identifier, form_with_incomplete_data=False)
    
    def search_assets(
        self,
        filter_query: AssetsFilterQuery,
        ignored_assets: Optional[set[str]] = None,
    ) -> list[dict[str, Any]]:
        """Search for assets based on filter criteria."""
        return self.globaldb.search_assets(
            filter_query=filter_query,
            ignored_assets_handling='exclude' if ignored_assets else 'none',
            ignored_asset_ids=ignored_assets,
        )
    
    def add_asset(
        self,
        asset_type: str,
        **kwargs,
    ) -> str:
        """Add a new asset to the database.
        
        Returns:
            The identifier of the created asset
        """
        return self.globaldb.add_asset(
            asset_type=asset_type,
            **kwargs,
        )
    
    def add_evm_token(
        self,
        address: ChecksumEvmAddress,
        chain_id: int,
        token_kind: str,
        decimals: int,
        name: str,
        symbol: str,
        **kwargs,
    ) -> str:
        """Add a new EVM token.
        
        Returns:
            The identifier of the created token
        """
        return self.globaldb.add_evm_token(
            address=address,
            chain_id=chain_id,
            token_kind=token_kind,
            decimals=decimals,
            name=name,
            symbol=symbol,
            **kwargs,
        )
    
    def edit_asset(
        self,
        identifier: str,
        **kwargs,
    ) -> None:
        """Edit an existing asset."""
        self.globaldb.edit_user_asset(identifier=identifier, **kwargs)
    
    def edit_evm_token(
        self,
        identifier: str,
        chain_id: int,
        address: ChecksumEvmAddress,
        decimals: int,
        name: Optional[str] = None,
        symbol: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Edit an existing EVM token.
        
        Returns:
            The identifier of the token
        """
        return self.globaldb.edit_evm_token(
            identifier=identifier,
            chain_id=chain_id,
            address=address,
            decimals=decimals,
            name=name,
            symbol=symbol,
            **kwargs,
        )
    
    def delete_asset(self, identifier: str) -> None:
        """Delete an asset by its identifier."""
        self.globaldb.delete_asset_by_identifier(identifier=identifier)
    
    def get_assets_mappings(self) -> dict[str, Any]:
        """Get mappings of nft and spam assets."""
        return self.globaldb.get_assets_mappings()
    
    def add_asset_identifiers(self, identifiers: list[str]) -> None:
        """Add multiple asset identifiers to user_owned_assets."""
        self.globaldb.add_asset_identifiers(identifiers=identifiers)
    
    def check_asset_exists(self, identifier: str) -> bool:
        """Check if an asset exists in the database."""
        return self.globaldb.get_asset_data(identifier=identifier, form_with_incomplete_data=True) is not None