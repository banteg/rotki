"""Queried addresses service for managing blockchain address queries"""
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


class QueriedAddressesService:
    """Service for managing queried blockchain addresses"""
    
    def __init__(self) -> None:
        # Would be initialized from app state
        self._db_conn: 'DBConnection | None' = None
        # In-memory storage for now
        self._queried_addresses: dict[str, set[str]] = {}
    
    def get_all_queried_addresses(self) -> dict[str, list[str]]:
        """Get all queried addresses grouped by blockchain"""
        # Would actually query from database
        result = {}
        for blockchain, addresses in self._queried_addresses.items():
            result[blockchain] = list(addresses)
        
        return result
    
    def add_queried_addresses(self, addresses: list[str], blockchain: str) -> int:
        """Add addresses to be queried for a blockchain"""
        # Validate blockchain
        valid_blockchains = ['ETH', 'BTC', 'BCH', 'DOT', 'KSM', 'AVAX', 'OPTIMISM']
        if blockchain not in valid_blockchains:
            raise ValueError(f'Invalid blockchain: {blockchain}')
        
        # Initialize set if needed
        if blockchain not in self._queried_addresses:
            self._queried_addresses[blockchain] = set()
        
        # Add addresses
        before_count = len(self._queried_addresses[blockchain])
        self._queried_addresses[blockchain].update(addresses)
        after_count = len(self._queried_addresses[blockchain])
        
        # Would actually store in database
        return after_count - before_count
    
    def remove_queried_addresses(self, addresses: list[str], blockchain: str) -> int:
        """Remove addresses from being queried"""
        # Validate blockchain
        if blockchain not in self._queried_addresses:
            return 0
        
        # Remove addresses
        before_count = len(self._queried_addresses[blockchain])
        self._queried_addresses[blockchain].difference_update(addresses)
        after_count = len(self._queried_addresses[blockchain])
        
        # Clean up empty sets
        if not self._queried_addresses[blockchain]:
            del self._queried_addresses[blockchain]
        
        # Would actually remove from database
        return before_count - after_count