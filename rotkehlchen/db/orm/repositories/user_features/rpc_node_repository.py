"""Repository for RPC node management"""

from typing import Optional

from sqlalchemy import select

from rotkehlchen.db.orm.models import RPCNode
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import ChainID, SupportedBlockchain


class RPCNodeRepository(BaseRepository[RPCNode]):
    """Repository for managing RPC nodes"""
    
    def __init__(self, session):
        super().__init__(session, RPCNode)
    
    def add_node(
        self,
        name: str,
        endpoint: str,
        blockchain: SupportedBlockchain,
        active: bool = True,
        weight: float = 1.0,
    ) -> RPCNode:
        """Add an RPC node"""
        node = RPCNode(
            name=name,
            endpoint=endpoint,
            blockchain=blockchain.serialize_for_db(),
            active=active,
            weight=str(weight),
        )
        return self.add(node)
    
    def get_node(self, identifier: int) -> Optional[RPCNode]:
        """Get a node by identifier"""
        return self.get(identifier=identifier)
    
    def get_nodes(
        self,
        blockchain: Optional[SupportedBlockchain] = None,
        active_only: bool = False,
    ) -> list[RPCNode]:
        """Get RPC nodes with optional filtering"""
        query = select(RPCNode)
        
        if blockchain:
            query = query.filter_by(blockchain=blockchain.serialize_for_db())
        
        if active_only:
            query = query.filter_by(active=True)
        
        # Order by weight descending (higher weight = higher priority)
        query = query.order_by(RPCNode.weight.desc())
        
        return list(self.session.execute(query).scalars().all())
    
    def get_active_nodes_for_blockchain(
        self,
        blockchain: SupportedBlockchain,
    ) -> list[RPCNode]:
        """Get all active nodes for a specific blockchain"""
        return self.get_nodes(blockchain=blockchain, active_only=True)
    
    def update_node(
        self,
        identifier: int,
        name: Optional[str] = None,
        endpoint: Optional[str] = None,
        active: Optional[bool] = None,
        weight: Optional[float] = None,
    ) -> Optional[RPCNode]:
        """Update an RPC node"""
        node = self.get_node(identifier)
        if not node:
            return None
        
        if name is not None:
            node.name = name
        if endpoint is not None:
            node.endpoint = endpoint
        if active is not None:
            node.active = active
        if weight is not None:
            node.weight = str(weight)
        
        return self.update(node)
    
    def delete_node(self, identifier: int) -> bool:
        """Delete an RPC node"""
        return self.delete_by(identifier=identifier) > 0
    
    def set_node_active_status(
        self,
        identifier: int,
        active: bool,
    ) -> Optional[RPCNode]:
        """Enable or disable a node"""
        return self.update_node(identifier, active=active)
    
    def get_node_by_endpoint(
        self,
        endpoint: str,
        blockchain: Optional[SupportedBlockchain] = None,
    ) -> Optional[RPCNode]:
        """Get a node by its endpoint"""
        query = select(RPCNode).filter_by(endpoint=endpoint)
        
        if blockchain:
            query = query.filter_by(blockchain=blockchain.serialize_for_db())
        
        return self.session.execute(query).scalar_one_or_none()
    
    def node_exists(
        self,
        endpoint: str,
        blockchain: SupportedBlockchain,
    ) -> bool:
        """Check if a node with endpoint and blockchain exists"""
        return self.get_node_by_endpoint(endpoint, blockchain) is not None
    
    def update_node_weight(
        self,
        identifier: int,
        weight: float,
    ) -> Optional[RPCNode]:
        """Update the weight/priority of a node"""
        return self.update_node(identifier, weight=weight)
    
    def get_default_nodes(self) -> list[RPCNode]:
        """Get all nodes marked as default"""
        # Default nodes typically have weight >= 10.0
        stmt = select(RPCNode).filter(
            RPCNode.weight >= '10.0'
        ).order_by(RPCNode.weight.desc())
        
        return list(self.session.execute(stmt).scalars().all())
    
    def reset_nodes_to_default(self, blockchain: SupportedBlockchain) -> None:
        """Reset all nodes for a blockchain to default state"""
        nodes = self.get_nodes(blockchain=blockchain)
        
        for node in nodes:
            # Set default nodes active, others inactive
            is_default = float(node.weight) >= 10.0
            node.active = is_default
            self.update(node)
    
    def count_active_nodes(self, blockchain: SupportedBlockchain) -> int:
        """Count active nodes for a blockchain"""
        query = select(func.count()).select_from(RPCNode).filter_by(
            blockchain=blockchain.serialize_for_db(),
            active=True,
        )
        return self.session.execute(query).scalar() or 0
    
    def bulk_update_nodes(
        self,
        updates: list[dict[str, any]],
    ) -> int:
        """Bulk update multiple nodes"""
        updated_count = 0
        
        for update_data in updates:
            identifier = update_data.pop('identifier', None)
            if identifier and self.update_node(identifier, **update_data):
                updated_count += 1
        
        return updated_count