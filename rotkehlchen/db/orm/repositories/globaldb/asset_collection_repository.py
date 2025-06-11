"""Repository for asset collections management"""

from typing import Optional

from sqlalchemy import func, or_, select

from rotkehlchen.db.orm.models import AssetCollection
from rotkehlchen.db.orm.repositories.base import BaseRepository


class AssetCollectionRepository(BaseRepository[AssetCollection]):
    """Repository for managing asset collections"""
    
    def __init__(self, session):
        super().__init__(session, AssetCollection)
    
    def add_collection(
        self,
        collection_id: int,
        name: str,
        symbol: str,
    ) -> AssetCollection:
        """Add an asset collection"""
        collection = AssetCollection(
            id=collection_id,
            name=name,
            symbol=symbol,
        )
        return self.add(collection)
    
    def get_collection(self, collection_id: int) -> Optional[AssetCollection]:
        """Get a collection by ID"""
        return self.get(id=collection_id)
    
    def get_collection_by_name(self, name: str) -> Optional[AssetCollection]:
        """Get a collection by name"""
        return self.get(name=name)
    
    def get_collection_by_symbol(self, symbol: str) -> Optional[AssetCollection]:
        """Get a collection by symbol"""
        return self.get(symbol=symbol)
    
    def get_all_collections(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[AssetCollection]:
        """Get all collections"""
        query = select(AssetCollection).order_by(AssetCollection.name)
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        
        return list(self.session.execute(query).scalars().all())
    
    def update_collection(
        self,
        collection_id: int,
        name: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> Optional[AssetCollection]:
        """Update a collection"""
        collection = self.get_collection(collection_id)
        if not collection:
            return None
        
        if name is not None:
            collection.name = name
        if symbol is not None:
            collection.symbol = symbol
        
        return self.update(collection)
    
    def delete_collection(self, collection_id: int) -> bool:
        """Delete a collection"""
        return self.delete_by(id=collection_id) > 0
    
    def collection_exists(self, collection_id: int) -> bool:
        """Check if a collection exists"""
        return self.get_collection(collection_id) is not None
    
    def search_collections(
        self,
        search_term: str,
        in_name: bool = True,
        in_symbol: bool = True,
    ) -> list[AssetCollection]:
        """Search collections by name and/or symbol"""
        query = select(AssetCollection)
        
        search_pattern = f'%{search_term}%'
        conditions = []
        
        if in_name:
            conditions.append(AssetCollection.name.like(search_pattern))
        if in_symbol:
            conditions.append(AssetCollection.symbol.like(search_pattern))
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        return list(self.session.execute(query).scalars().all())
    
    def get_collections_count(self) -> int:
        """Get total count of collections"""
        query = select(func.count()).select_from(AssetCollection)
        return self.session.execute(query).scalar() or 0
    
    def bulk_add_collections(
        self,
        collections_data: list[dict[str, any]],
    ) -> list[AssetCollection]:
        """Bulk add multiple collections"""
        collections = []
        
        for data in collections_data:
            collection = AssetCollection(
                id=data['id'],
                name=data['name'],
                symbol=data['symbol'],
            )
            self.session.add(collection)
            collections.append(collection)
        
        self.session.flush()
        return collections
    
    def get_collections_by_ids(
        self,
        collection_ids: list[int],
    ) -> list[AssetCollection]:
        """Get multiple collections by IDs"""
        if not collection_ids:
            return []
        
        stmt = select(AssetCollection).filter(
            AssetCollection.id.in_(collection_ids)
        ).order_by(AssetCollection.name)
        
        return list(self.session.execute(stmt).scalars().all())