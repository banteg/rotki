"""Repository for address book management"""

from typing import Optional

from sqlalchemy import delete, func, or_, select

from rotkehlchen.db.orm.models import AddressBook
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain


class AddressBookRepository(BaseRepository[AddressBook]):
    """Repository for managing address book entries"""
    
    def __init__(self, session):
        super().__init__(session, AddressBook)
    
    def add_entry(
        self,
        name: str,
        address: ChecksumEvmAddress,
        blockchain: Optional[SupportedBlockchain] = None,
    ) -> AddressBook:
        """Add an address book entry"""
        entry = AddressBook(
            name=name,
            address=address,
            blockchain=blockchain.serialize_for_db() if blockchain else None,
        )
        return self.add(entry)
    
    def get_entry(self, identifier: int) -> Optional[AddressBook]:
        """Get an entry by identifier"""
        return self.get(identifier=identifier)
    
    def get_entry_by_address(
        self,
        address: ChecksumEvmAddress,
        blockchain: Optional[SupportedBlockchain] = None,
    ) -> Optional[AddressBook]:
        """Get entry by address and optional blockchain"""
        query = select(AddressBook).filter_by(address=address)
        
        if blockchain:
            query = query.filter_by(blockchain=blockchain.serialize_for_db())
        
        return self.session.execute(query).scalar_one_or_none()
    
    def get_entries(
        self,
        name: Optional[str] = None,
        blockchain: Optional[SupportedBlockchain] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[AddressBook]:
        """Get address book entries with filters"""
        query = select(AddressBook)
        
        if name:
            query = query.filter(AddressBook.name.like(f'%{name}%'))
        
        if blockchain:
            query = query.filter_by(blockchain=blockchain.serialize_for_db())
        
        # Order by name
        query = query.order_by(AddressBook.name)
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        
        return list(self.session.execute(query).scalars().all())
    
    def update_entry(
        self,
        identifier: int,
        name: Optional[str] = None,
        address: Optional[ChecksumEvmAddress] = None,
        blockchain: Optional[SupportedBlockchain] = None,
    ) -> Optional[AddressBook]:
        """Update an address book entry"""
        entry = self.get_entry(identifier)
        if not entry:
            return None
        
        if name is not None:
            entry.name = name
        if address is not None:
            entry.address = address
        if blockchain is not None:
            entry.blockchain = blockchain.serialize_for_db()
        
        return self.update(entry)
    
    def delete_entry(self, identifier: int) -> bool:
        """Delete an address book entry"""
        return self.delete_by(identifier=identifier) > 0
    
    def entry_exists(
        self,
        address: ChecksumEvmAddress,
        blockchain: Optional[SupportedBlockchain] = None,
    ) -> bool:
        """Check if entry exists for address"""
        return self.get_entry_by_address(address, blockchain) is not None
    
    def search_entries(self, search_term: str) -> list[AddressBook]:
        """Search entries by name or address"""
        stmt = select(AddressBook).filter(
            or_(
                AddressBook.name.like(f'%{search_term}%'),
                AddressBook.address.like(f'%{search_term}%'),
            )
        ).order_by(AddressBook.name)
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_names_for_address(
        self,
        address: ChecksumEvmAddress,
    ) -> list[str]:
        """Get all names associated with an address"""
        stmt = select(AddressBook.name).filter_by(
            address=address
        ).distinct()
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_addresses_for_name(self, name: str) -> list[ChecksumEvmAddress]:
        """Get all addresses associated with a name"""
        stmt = select(AddressBook.address).filter_by(
            name=name
        ).distinct()
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_entries_count(
        self,
        blockchain: Optional[SupportedBlockchain] = None,
    ) -> int:
        """Get count of entries"""
        query = select(func.count()).select_from(AddressBook)
        
        if blockchain:
            query = query.filter_by(blockchain=blockchain.serialize_for_db())
        
        return self.session.execute(query).scalar() or 0
    
    def bulk_add_entries(
        self,
        entries_data: list[dict[str, any]],
    ) -> list[AddressBook]:
        """Bulk add multiple entries"""
        entries = []
        
        for data in entries_data:
            entry = AddressBook(
                name=data['name'],
                address=data['address'],
                blockchain=data.get('blockchain', '').serialize_for_db() if data.get('blockchain') else None,
            )
            self.session.add(entry)
            entries.append(entry)
        
        self.session.flush()
        return entries
    
    def rename_entries(
        self,
        old_name: str,
        new_name: str,
    ) -> int:
        """Rename all entries with a specific name"""
        entries = self.get_entries(name=old_name)
        
        for entry in entries:
            entry.name = new_name
        
        self.session.flush()
        return len(entries)
    
    def delete_entries_by_blockchain(
        self,
        blockchain: SupportedBlockchain,
    ) -> int:
        """Delete all entries for a blockchain"""
        stmt = delete(AddressBook).filter_by(
            blockchain=blockchain.serialize_for_db()
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount