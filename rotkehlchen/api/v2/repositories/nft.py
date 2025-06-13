"""Repository for managing NFTs."""
from typing import TYPE_CHECKING, Optional

from sqlmodel import func, select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.asset import NFT

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class NFTRepository(BaseRepository[NFT]):
    """Repository for managing NFTs."""
    
    model = NFT
    
    def get_nfts_by_owner(
        self,
        owner_address: 'ChecksumEvmAddress',
        collection: Optional[str] = None,
    ) -> list[NFT]:
        """Get all NFTs owned by a specific address."""
        query = select(self.model).where(self.model.last_owner == owner_address)
        
        if collection:
            query = query.where(self.model.collection == collection)
        
        result = self.session.exec(query)
        return list(result.all())
    
    def get_nfts_by_collection(
        self,
        collection: str,
        limit: Optional[int] = None,
    ) -> list[NFT]:
        """Get all NFTs from a specific collection."""
        query = select(self.model).where(self.model.collection == collection)
        
        if limit:
            query = query.limit(limit)
        
        result = self.session.exec(query)
        return list(result.all())
    
    def get_nft_by_identifier(
        self,
        identifier: str,
    ) -> Optional[NFT]:
        """Get a specific NFT by its identifier."""
        query = select(self.model).where(self.model.identifier == identifier)
        result = self.session.exec(query).first()
        return result
    
    def update_nft_price(
        self,
        identifier: str,
        price_asset: str,
        price_in_asset: str,
        manual_price: bool = False,
    ) -> Optional[NFT]:
        """Update the price of an NFT."""
        nft = self.get_nft_by_identifier(identifier)
        
        if nft:
            nft.price_asset = price_asset
            nft.price_in_asset = price_in_asset
            nft.manual_price = manual_price
            self.session.add(nft)
            self.session.commit()
            return nft
        return None
    
    def get_collections_by_owner(
        self,
        owner_address: 'ChecksumEvmAddress',
    ) -> list[str]:
        """Get all unique collections owned by an address."""
        query = (
            select(self.model.collection)
            .where(self.model.last_owner == owner_address)
            .distinct()
        )
        result = self.session.exec(query)
        return list(result.all())
    
    def count_nfts_by_owner(
        self,
        owner_address: 'ChecksumEvmAddress',
    ) -> int:
        """Count the total number of NFTs owned by an address."""
        query = select(func.count(self.model.identifier)).where(
            self.model.last_owner == owner_address
        )
        result = self.session.exec(query).one()
        return result
    
    def get_nfts_with_manual_price(self) -> list[NFT]:
        """Get all NFTs that have manual prices set."""
        query = select(self.model).where(self.model.manual_price == True)  # noqa: E712
        result = self.session.exec(query)
        return list(result.all())
    
    def batch_update_owner(
        self,
        nft_identifiers: list[str],
        new_owner: 'ChecksumEvmAddress',
    ) -> int:
        """Update the owner for multiple NFTs at once."""
        updated_count = 0
        
        for identifier in nft_identifiers:
            nft = self.get_nft_by_identifier(identifier)
            if nft:
                nft.last_owner = new_owner
                self.session.add(nft)
                updated_count += 1
        
        if updated_count > 0:
            self.session.commit()
        
        return updated_count
    
    def search_nfts(
        self,
        search_term: str,
        limit: int = 50,
    ) -> list[NFT]:
        """Search NFTs by name or collection."""
        query = select(self.model).where(
            (self.model.name.contains(search_term)) |
            (self.model.collection.contains(search_term))
        ).limit(limit)
        
        result = self.session.exec(query)
        return list(result.all())
    
    def get_nfts_with_images(
        self,
        owner_address: Optional['ChecksumEvmAddress'] = None,
    ) -> list[NFT]:
        """Get NFTs that have image URLs."""
        query = select(self.model).where(self.model.image_url.is_not(None))
        
        if owner_address:
            query = query.where(self.model.last_owner == owner_address)
        
        result = self.session.exec(query)
        return list(result.all())