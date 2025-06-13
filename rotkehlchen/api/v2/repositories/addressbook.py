"""Repository for managing address book entries."""
from typing import TYPE_CHECKING, Optional

from sqlmodel import func, select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.addressbook import AddressBook

if TYPE_CHECKING:
    from rotkehlchen.types import AddressBookType, ChecksumEvmAddress, SupportedBlockchain


class AddressBookRepository(BaseRepository[AddressBook]):
    """Repository for managing address book entries."""
    
    model = AddressBook
    
    def get_entry(
        self,
        address: 'ChecksumEvmAddress',
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> Optional[AddressBook]:
        """Get a specific address book entry."""
        query = select(self.model).where(self.model.address == address)
        
        if blockchain is not None:
            query = query.where(self.model.blockchain == blockchain.value)
        
        result = self.session.exec(query).first()
        return result
    
    def get_entries_by_type(
        self,
        book_type: 'AddressBookType',
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> list[AddressBook]:
        """Get all entries of a specific type."""
        query = select(self.model).where(self.model.book_type == book_type.value)
        
        if blockchain is not None:
            query = query.where(self.model.blockchain == blockchain.value)
        
        query = query.order_by(self.model.name)
        result = self.session.exec(query)
        return list(result.all())
    
    def add_entry(
        self,
        book_type: 'AddressBookType',
        address: 'ChecksumEvmAddress',
        name: str,
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> AddressBook:
        """Add a new address book entry."""
        entry_data = {
            'book_type': book_type.value,
            'address': address,
            'name': name,
            'blockchain': blockchain.value if blockchain else None,
        }
        return self.create(entry_data)
    
    def update_entry(
        self,
        address: 'ChecksumEvmAddress',
        name: Optional[str] = None,
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> Optional[AddressBook]:
        """Update an existing address book entry."""
        entry = self.get_entry(address, blockchain)
        if not entry:
            return None
        
        if name is not None:
            entry.name = name
        
        self.session.add(entry)
        self.session.commit()
        return entry
    
    def delete_entry(
        self,
        address: 'ChecksumEvmAddress',
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> bool:
        """Delete an address book entry."""
        entry = self.get_entry(address, blockchain)
        
        if entry:
            self.session.delete(entry)
            self.session.commit()
            return True
        return False
    
    def search_entries(
        self,
        search_term: str,
        book_type: Optional['AddressBookType'] = None,
        blockchain: Optional['SupportedBlockchain'] = None,
        limit: int = 50,
    ) -> list[AddressBook]:
        """Search address book entries by name or address."""
        query = select(self.model).where(
            (func.lower(self.model.name).contains(search_term.lower())) |
            (func.lower(self.model.address).contains(search_term.lower()))
        )
        
        if book_type is not None:
            query = query.where(self.model.book_type == book_type.value)
        
        if blockchain is not None:
            query = query.where(self.model.blockchain == blockchain.value)
        
        query = query.order_by(self.model.name).limit(limit)
        result = self.session.exec(query)
        return list(result.all())
    
    def get_entries_by_blockchain(
        self,
        blockchain: 'SupportedBlockchain',
    ) -> list[AddressBook]:
        """Get all entries for a specific blockchain."""
        query = select(self.model).where(
            self.model.blockchain == blockchain.value
        ).order_by(self.model.name)
        
        result = self.session.exec(query)
        return list(result.all())
    
    def count_entries(
        self,
        book_type: Optional['AddressBookType'] = None,
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> int:
        """Count address book entries."""
        query = select(func.count(self.model.identifier))
        
        if book_type is not None:
            query = query.where(self.model.book_type == book_type.value)
        
        if blockchain is not None:
            query = query.where(self.model.blockchain == blockchain.value)
        
        result = self.session.exec(query).one()
        return result
    
    def entry_exists(
        self,
        address: 'ChecksumEvmAddress',
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> bool:
        """Check if an entry exists."""
        return self.get_entry(address, blockchain) is not None
    
    def get_global_entries(self) -> list[AddressBook]:
        """Get all global address book entries (not blockchain-specific)."""
        query = select(self.model).where(
            self.model.book_type == 'global'
        ).order_by(self.model.name)
        
        result = self.session.exec(query)
        return list(result.all())
    
    def migrate_to_blockchain_specific(
        self,
        address: 'ChecksumEvmAddress',
        from_blockchain: Optional['SupportedBlockchain'],
        to_blockchain: 'SupportedBlockchain',
    ) -> Optional[AddressBook]:
        """Migrate an entry from one blockchain to another."""
        entry = self.get_entry(address, from_blockchain)
        if not entry:
            return None
        
        # Check if target already exists
        if self.entry_exists(address, to_blockchain):
            return None
        
        # Update blockchain
        entry.blockchain = to_blockchain.value
        self.session.add(entry)
        self.session.commit()
        return entry