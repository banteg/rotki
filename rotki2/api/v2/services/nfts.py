"""NFT service for managing NFT operations"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.modules.nft.constants import FREE_NFT_LIMIT
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.db.filtering import NFTFilterQuery
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.premium.premium import premium_create_and_verify
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotki2.api.v2.repositories.nft import NFTRepository
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.ethereum.modules.nft.nfts import Nfts
    from rotkehlchen.data_handler import DataHandler


class NFTService:
    """Service for NFT-related operations"""

    def __init__(
        self,
        db_connection: DBConnection,
        nft_repository: 'NFTRepository | None' = None,
        chains_aggregator: 'ChainsAggregator | None' = None,
        data_handler: 'DataHandler | None' = None,
    ):
        self.db_connection = db_connection
        self.nft_repository = nft_repository
        self.chains_aggregator = chains_aggregator
        self.data = data_handler
        self._nft_module: Nfts | None = None

    @property
    def nft_module(self) -> 'Nfts':
        """Get the NFT module from chains aggregator"""
        if self._nft_module is None:
            if self.chains_aggregator is None:
                raise ValueError('Chains aggregator not initialized')

            eth_manager = self.chains_aggregator.get_chain_manager('ETH')
            if eth_manager is None:
                raise ValueError('Ethereum manager not found')

            self._nft_module = eth_manager.node_inquirer.get_module('nfts')
            if self._nft_module is None:
                raise ValueError('NFT module not found')

        return self._nft_module

    def get_all_nfts(self, ignore_cache: bool = False) -> dict[str, Any]:
        """Get all NFT information for configured addresses"""
        try:
            result = self.nft_module.get_all_info(
                addresses=self._get_tracked_addresses(),
                ignore_cache=ignore_cache,
            )

            # Check premium limits
            nfts_num = len(result.addresses)
            limit_hit = False
            premium_active = self._check_premium()

            if not premium_active and nfts_num > FREE_NFT_LIMIT:
                limit_hit = True
                # Truncate results for free users
                addresses = list(result.addresses.items())[:FREE_NFT_LIMIT]
                result = result._replace(addresses=dict(addresses))

            return {
                'addresses': self._serialize_nft_result(result),
                'total': result.total_usd_value,
                'premium': premium_active,
                'premium_only': limit_hit,
            }

        except RemoteError as e:
            return {
                'error': str(e),
                'addresses': {},
                'total': '0',
            }

    def get_nft_balances(
        self,
        filter_query: NFTFilterQuery,
        ignore_cache: bool = False,
    ) -> dict[str, Any]:
        """Get NFT balances from database with filtering"""
        balances = self.nft_module.get_db_nft_balances(filter_query=filter_query)

        # Check premium limits
        entries_found = len(balances)
        entries_limit = FREE_NFT_LIMIT if not self._check_premium() else -1

        if entries_limit != -1 and entries_found > entries_limit:
            balances = balances[:entries_limit]

        return {
            'entries': [self._serialize_nft_balance(b) for b in balances],
            'entries_found': entries_found,
            'entries_limit': entries_limit,
        }

    def get_nfts_with_price(self, lps_handling: NftLpHandling) -> dict[str, Any]:
        """Get NFTs that have a price set"""
        nfts_with_price = self.nft_module.get_nfts_with_price(lps_handling=lps_handling)

        return {
            'nfts': [
                {
                    'asset': nft[0].identifier,
                    'name': nft[0].name,
                    'collection': nft[0].collection.name if nft[0].collection else None,
                    'price_asset': nft[1].identifier,
                    'price': str(nft[2]),
                    'manual_price': nft[3],
                }
                for nft in nfts_with_price
            ],
        }

    def add_manual_nft_price(
        self,
        asset: str,
        price: str,
        price_asset: str,
    ) -> dict[str, str]:
        """Add manual price for an NFT"""
        from rotkehlchen.assets.asset import Asset
        from rotkehlchen.assets.types import AssetType
        from rotkehlchen.fval import FVal

        # Verify it's an NFT
        asset_obj = Asset(asset)
        if asset_obj.asset_type != AssetType.NFT:
            raise ValueError(f'{asset} is not an NFT')

        # If we have a repository, use it to update the price
        if self.nft_repository:
            updated_nft = self.nft_repository.update_nft_price(
                identifier=asset,
                price_asset=price_asset,
                price_in_asset=price,
                manual_price=True,
            )
            if not updated_nft:
                # NFT not in database, add it via the module
                self.nft_module.add_nft_with_price(
                    nft=asset_obj,
                    price=FVal(price),
                    price_asset=Asset(price_asset),
                )
        else:
            # Fallback to module method
            self.nft_module.add_nft_with_price(
                nft=asset_obj,
                price=FVal(price),
                price_asset=Asset(price_asset),
            )

        return {'message': f'Manual price added for NFT {asset}'}

    def delete_manual_nft_price(self, asset: str) -> dict[str, str]:
        """Delete manual price for an NFT"""
        from rotkehlchen.assets.asset import Asset
        from rotkehlchen.assets.types import AssetType

        # Verify it's an NFT
        asset_obj = Asset(asset)
        if asset_obj.asset_type != AssetType.NFT:
            raise ValueError(f'{asset} is not an NFT')

        # Delete the manual price
        self.nft_module.delete_price_for_nft(nft=asset_obj)

        return {'message': f'Manual price deleted for NFT {asset}'}

    def _get_tracked_addresses(self) -> list[ChecksumEvmAddress]:
        """Get all tracked Ethereum addresses"""
        if self.chains_aggregator is None:
            return []

        eth_accounts = self.chains_aggregator.accounts.eth
        return list(eth_accounts) if eth_accounts else []

    def _check_premium(self) -> bool:
        """Check if premium is active"""
        if self.data is None:
            return False

        premium = premium_create_and_verify(self.data.db)
        return premium is not None and premium.is_active()

    def _serialize_nft_result(self, result) -> dict[str, Any]:
        """Serialize NFT result to API format"""
        serialized = {}
        for address, nfts in result.addresses.items():
            serialized[address] = [
                {
                    'id': nft.token_identifier,
                    'asset': nft.asset.identifier,
                    'name': nft.name,
                    'image_url': nft.image_url,
                    'collection': {
                        'name': nft.collection.name,
                        'banner_image': nft.collection.banner_image,
                        'description': nft.collection.description,
                        'large_image': nft.collection.large_image,
                    } if nft.collection else None,
                    'price_in_asset': str(nft.price_in_asset) if nft.price_in_asset else None,
                    'price_asset': nft.price_asset.identifier if nft.price_asset else None,
                    'manually_input': nft.manually_input,
                    'usd_price': str(nft.usd_price) if nft.usd_price else None,
                }
                for nft in nfts
            ]
        return serialized

    def _serialize_nft_balance(self, balance) -> dict[str, Any]:
        """Serialize NFT balance entry"""
        return {
            'id': balance.id,
            'name': balance.name,
            'asset': balance.asset.identifier,
            'collection_name': balance.collection_name,
            'usd_price': str(balance.usd_price) if balance.usd_price else '0',
            'manual_price': balance.manual_price,
            'owner_address': balance.owner_address,
            'is_lp': balance.is_lp,
            'image_url': balance.image_url,
        }
