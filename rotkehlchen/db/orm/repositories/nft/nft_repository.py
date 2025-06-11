"""Repository for NFT management"""

from typing import Optional

from sqlalchemy import select

from rotkehlchen.db.orm.models import NFT
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress


class NFTRepository(BaseRepository[NFT]):
    """Repository for managing NFTs"""
    
    def __init__(self, session):
        super().__init__(session, NFT)
    
    def add_nft(
        self,
        identifier: str,
        name: str,
        last_price: FVal,
        last_price_asset: str,
        manual_price: bool = False,
        owner_address: Optional[ChecksumEvmAddress] = None,
        blockchain: Optional[str] = None,
        is_lp: bool = False,
        image_url: Optional[str] = None,
        collection_id: Optional[str] = None,
    ) -> NFT:
        """Add an NFT"""
        nft = NFT(
            identifier=identifier,
            name=name,
            last_price=str(last_price),
            last_price_asset=last_price_asset,
            manual_price=manual_price,
            owner_address=owner_address,
            blockchain=blockchain,
            is_lp=is_lp,
            image_url=image_url,
            collection_id=collection_id,
        )
        return self.add(nft)
    
    def get_nft(self, identifier: str) -> Optional[NFT]:
        """Get an NFT by identifier"""
        return self.get(identifier=identifier)
    
    def get_nfts(
        self,
        owner_address: Optional[ChecksumEvmAddress] = None,
        blockchain: Optional[str] = None,
        collection_id: Optional[str] = None,
        is_lp: Optional[bool] = None,
        manual_price: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[NFT]:
        """Get NFTs with filters"""
        query = select(NFT)
        
        if owner_address:
            query = query.filter_by(owner_address=owner_address)
        
        if blockchain:
            query = query.filter_by(blockchain=blockchain)
        
        if collection_id:
            query = query.filter_by(collection_id=collection_id)
        
        if is_lp is not None:
            query = query.filter_by(is_lp=is_lp)
        
        if manual_price is not None:
            query = query.filter_by(manual_price=manual_price)
        
        # Order by name
        query = query.order_by(NFT.name)
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        
        return list(self.session.execute(query).scalars().all())
    
    def update_nft_price(
        self,
        identifier: str,
        last_price: FVal,
        last_price_asset: str,
        manual_price: bool = False,
    ) -> Optional[NFT]:
        """Update NFT price information"""
        nft = self.get_nft(identifier)
        if not nft:
            return None
        
        nft.last_price = str(last_price)
        nft.last_price_asset = last_price_asset
        nft.manual_price = manual_price
        
        return self.update(nft)
    
    def update_nft_metadata(
        self,
        identifier: str,
        name: Optional[str] = None,
        image_url: Optional[str] = None,
        owner_address: Optional[ChecksumEvmAddress] = None,
    ) -> Optional[NFT]:
        """Update NFT metadata"""
        nft = self.get_nft(identifier)
        if not nft:
            return None
        
        if name is not None:
            nft.name = name
        if image_url is not None:
            nft.image_url = image_url
        if owner_address is not None:
            nft.owner_address = owner_address
        
        return self.update(nft)
    
    def delete_nft(self, identifier: str) -> bool:
        """Delete an NFT"""
        return self.delete_by(identifier=identifier) > 0
    
    def nft_exists(self, identifier: str) -> bool:
        """Check if an NFT exists"""
        return self.get_nft(identifier) is not None
    
    def get_nfts_by_owner(
        self,
        owner_address: ChecksumEvmAddress,
    ) -> list[NFT]:
        """Get all NFTs owned by an address"""
        stmt = select(NFT).filter_by(
            owner_address=owner_address
        ).order_by(NFT.name)
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_nfts_by_collection(
        self,
        collection_id: str,
    ) -> list[NFT]:
        """Get all NFTs in a collection"""
        stmt = select(NFT).filter_by(
            collection_id=collection_id
        ).order_by(NFT.name)
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_total_value(
        self,
        owner_address: Optional[ChecksumEvmAddress] = None,
        price_asset: Optional[str] = None,
    ) -> FVal:
        """Get total value of NFTs"""
        query = select(func.sum(NFT.last_price))
        
        if owner_address:
            query = query.filter_by(owner_address=owner_address)
        if price_asset:
            query = query.filter_by(last_price_asset=price_asset)
        
        result = self.session.execute(query).scalar()
        return FVal(result) if result else FVal(0)
    
    def get_nfts_count(
        self,
        owner_address: Optional[ChecksumEvmAddress] = None,
        blockchain: Optional[str] = None,
    ) -> int:
        """Get count of NFTs"""
        query = select(func.count()).select_from(NFT)
        
        if owner_address:
            query = query.filter_by(owner_address=owner_address)
        if blockchain:
            query = query.filter_by(blockchain=blockchain)
        
        return self.session.execute(query).scalar() or 0
    
    def get_unique_collections(self) -> list[str]:
        """Get list of unique collection IDs"""
        stmt = select(NFT.collection_id).distinct().filter(
            NFT.collection_id.isnot(None)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_lp_nfts(self) -> list[NFT]:
        """Get all LP position NFTs"""
        stmt = select(NFT).filter_by(is_lp=True).order_by(NFT.name)
        return list(self.session.execute(stmt).scalars().all())
    
    def get_manually_priced_nfts(self) -> list[NFT]:
        """Get all NFTs with manual pricing"""
        stmt = select(NFT).filter_by(manual_price=True).order_by(NFT.name)
        return list(self.session.execute(stmt).scalars().all())
    
    def transfer_nft(
        self,
        identifier: str,
        new_owner: ChecksumEvmAddress,
    ) -> Optional[NFT]:
        """Transfer NFT to new owner"""
        return self.update_nft_metadata(identifier, owner_address=new_owner)
    
    def bulk_add_nfts(
        self,
        nfts_data: list[dict[str, any]],
    ) -> list[NFT]:
        """Bulk add multiple NFTs"""
        nfts = []
        
        for data in nfts_data:
            nft = NFT(
                identifier=data['identifier'],
                name=data['name'],
                last_price=str(data['last_price']),
                last_price_asset=data['last_price_asset'],
                manual_price=data.get('manual_price', False),
                owner_address=data.get('owner_address'),
                blockchain=data.get('blockchain'),
                is_lp=data.get('is_lp', False),
                image_url=data.get('image_url'),
                collection_id=data.get('collection_id'),
            )
            self.session.add(nft)
            nfts.append(nft)
        
        self.session.flush()
        return nfts