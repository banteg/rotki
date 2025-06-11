"""EVM node management using ORM"""

import logging
import time
from typing import TYPE_CHECKING, Any

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.orm.database import RotkehlchenDatabase
    from rotkehlchen.globaldb.handler import GlobalDBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def populate_rpc_nodes_in_database_orm(
        db: 'RotkehlchenDatabase',
) -> None:
    """Populate initial RPC nodes in database using ORM
    
    This function is called when creating a new database to add default nodes
    """
    # Default nodes configuration
    default_nodes = {
        SupportedBlockchain.ETHEREUM: [
            {
                'name': 'etherscan',
                'endpoint': 'https://api.etherscan.io/api',
                'owned': False,
                'active': True,
                'weight': 0.2,
                'blockchain': 'ETH',
            },
            {
                'name': 'cloudflare-eth',
                'endpoint': 'https://cloudflare-eth.com',
                'owned': False,
                'active': True,
                'weight': 0.15,
                'blockchain': 'ETH',
            },
            {
                'name': 'public-node',
                'endpoint': 'https://ethereum.publicnode.com',
                'owned': False,
                'active': True,
                'weight': 0.1,
                'blockchain': 'ETH',
            },
        ],
        SupportedBlockchain.OPTIMISM: [
            {
                'name': 'optimism-etherscan',
                'endpoint': 'https://api-optimistic.etherscan.io/api',
                'owned': False,
                'active': True,
                'weight': 0.2,
                'blockchain': 'OPTIMISM',
            },
            {
                'name': 'optimism-official',
                'endpoint': 'https://mainnet.optimism.io',
                'owned': False,
                'active': True,
                'weight': 0.15,
                'blockchain': 'OPTIMISM',
            },
        ],
        SupportedBlockchain.POLYGON_POS: [
            {
                'name': 'polygon-etherscan',
                'endpoint': 'https://api.polygonscan.com/api',
                'owned': False,
                'active': True,
                'weight': 0.2,
                'blockchain': 'POLYGON_POS',
            },
            {
                'name': 'polygon-official',
                'endpoint': 'https://polygon-rpc.com',
                'owned': False,
                'active': True,
                'weight': 0.15,
                'blockchain': 'POLYGON_POS',
            },
        ],
        SupportedBlockchain.ARBITRUM_ONE: [
            {
                'name': 'arbitrum-etherscan',
                'endpoint': 'https://api.arbiscan.io/api',
                'owned': False,
                'active': True,
                'weight': 0.2,
                'blockchain': 'ARBITRUM_ONE',
            },
            {
                'name': 'arbitrum-official',
                'endpoint': 'https://arb1.arbitrum.io/rpc',
                'owned': False,
                'active': True,
                'weight': 0.15,
                'blockchain': 'ARBITRUM_ONE',
            },
        ],
        SupportedBlockchain.BASE: [
            {
                'name': 'base-etherscan',
                'endpoint': 'https://api.basescan.org/api',
                'owned': False,
                'active': True,
                'weight': 0.2,
                'blockchain': 'BASE',
            },
            {
                'name': 'base-official',
                'endpoint': 'https://mainnet.base.org',
                'owned': False,
                'active': True,
                'weight': 0.15,
                'blockchain': 'BASE',
            },
        ],
        SupportedBlockchain.GNOSIS: [
            {
                'name': 'gnosis-etherscan',
                'endpoint': 'https://api.gnosisscan.io/api',
                'owned': False,
                'active': True,
                'weight': 0.2,
                'blockchain': 'GNOSIS',
            },
            {
                'name': 'gnosis-official',
                'endpoint': 'https://rpc.gnosischain.com',
                'owned': False,
                'active': True,
                'weight': 0.15,
                'blockchain': 'GNOSIS',
            },
        ],
        SupportedBlockchain.SCROLL: [
            {
                'name': 'scroll-etherscan',
                'endpoint': 'https://api.scrollscan.com/api',
                'owned': False,
                'active': True,
                'weight': 0.2,
                'blockchain': 'SCROLL',
            },
            {
                'name': 'scroll-official',
                'endpoint': 'https://rpc.scroll.io',
                'owned': False,
                'active': True,
                'weight': 0.15,
                'blockchain': 'SCROLL',
            },
        ],
    }
    
    # Add nodes to database using ORM
    with db.repos.unit_of_work():
        for blockchain, nodes in default_nodes.items():
            for node_data in nodes:
                try:
                    db.repos.rpc_nodes.add_node(
                        identifier=node_data['name'],
                        name=node_data['name'],
                        endpoint=node_data['endpoint'],
                        owned=node_data['owned'],
                        active=node_data['active'],
                        weight=str(node_data['weight']),
                        blockchain=node_data['blockchain'],
                    )
                    log.debug(f"Added default RPC node {node_data['name']} for {blockchain}")
                except Exception as e:
                    log.warning(f"Failed to add default node {node_data['name']}: {e}")


class EVMNodeManager:
    """Manages EVM nodes using ORM"""
    
    def __init__(self, db: 'RotkehlchenDatabase'):
        self.db = db
    
    def get_nodes_for_blockchain(
            self,
            blockchain: SupportedBlockchain,
            only_active: bool = True,
    ) -> list[dict[str, Any]]:
        """Get RPC nodes for a specific blockchain using ORM"""
        nodes = self.db.repos.rpc_nodes.get_nodes_by_blockchain(
            blockchain=blockchain.serialize(),
            only_active=only_active,
        )
        
        return [
            {
                'identifier': node.identifier,
                'name': node.name,
                'endpoint': node.endpoint,
                'owned': node.owned,
                'active': node.active,
                'weight': node.weight,
                'blockchain': node.blockchain,
            }
            for node in nodes
        ]
    
    def add_node(
            self,
            name: str,
            endpoint: str,
            blockchain: SupportedBlockchain,
            owned: bool = True,
            active: bool = True,
            weight: str = '0.1',
    ) -> str:
        """Add a new RPC node using ORM
        
        Returns the identifier of the added node
        """
        with self.db.repos.unit_of_work():
            # Generate unique identifier
            identifier = f"{blockchain.serialize().lower()}_{name.lower().replace(' ', '_')}"
            
            success = self.db.repos.rpc_nodes.add_node(
                identifier=identifier,
                name=name,
                endpoint=endpoint,
                owned=owned,
                active=active,
                weight=weight,
                blockchain=blockchain.serialize(),
            )
            
            if not success:
                raise ValueError(f"Node with identifier {identifier} already exists")
            
            log.info(f"Added RPC node {name} for {blockchain}")
            return identifier
    
    def update_node(
            self,
            identifier: str,
            name: str | None = None,
            endpoint: str | None = None,
            active: bool | None = None,
            weight: str | None = None,
    ) -> bool:
        """Update an existing RPC node using ORM
        
        Returns True if node was updated, False if not found
        """
        with self.db.repos.unit_of_work():
            updated = self.db.repos.rpc_nodes.update_node(
                identifier=identifier,
                name=name,
                endpoint=endpoint,
                active=active,
                weight=weight,
            )
            
            if updated:
                log.info(f"Updated RPC node {identifier}")
            else:
                log.warning(f"RPC node {identifier} not found for update")
            
            return updated
    
    def delete_node(self, identifier: str) -> bool:
        """Delete an RPC node using ORM
        
        Returns True if node was deleted, False if not found
        """
        with self.db.repos.unit_of_work():
            # Check if node is owned
            node = self.db.repos.rpc_nodes.get_node(identifier)
            if not node:
                return False
            
            if not node.owned:
                raise ValueError("Cannot delete non-owned RPC nodes")
            
            success = self.db.repos.rpc_nodes.delete_node(identifier)
            
            if success:
                log.info(f"Deleted RPC node {identifier}")
            
            return success
    
    def get_node_connection_statistics(self, identifier: str) -> dict[str, Any]:
        """Get connection statistics for a node using ORM"""
        # TODO: This would need a node_statistics table to track:
        # TODO: - Last successful connection
        # TODO: - Total requests
        # TODO: - Failed requests
        # TODO: - Average response time
        
        node = self.db.repos.rpc_nodes.get_node(identifier)
        if not node:
            raise ValueError(f"Node {identifier} not found")
        
        # Placeholder statistics
        return {
            'identifier': identifier,
            'last_connected': None,
            'total_requests': 0,
            'failed_requests': 0,
            'success_rate': 100.0,
            'avg_response_time': 0.0,
        }
    
    def record_node_request(
            self,
            identifier: str,
            success: bool,
            response_time: float | None = None,
    ) -> None:
        """Record a request to a node for statistics using ORM"""
        # TODO: Implement node statistics tracking
        # TODO: This would update node_statistics table
        pass
    
    def reorder_nodes(
            self,
            blockchain: SupportedBlockchain,
            node_order: list[str],
    ) -> None:
        """Reorder nodes by updating their weights using ORM"""
        with self.db.repos.unit_of_work():
            # Calculate new weights based on order
            weight_step = 1.0 / (len(node_order) + 1)
            
            for idx, identifier in enumerate(node_order):
                new_weight = str(1.0 - (idx + 1) * weight_step)
                self.db.repos.rpc_nodes.update_node(
                    identifier=identifier,
                    weight=new_weight,
                )
            
            log.info(f"Reordered {len(node_order)} nodes for {blockchain}")
    
    def get_all_nodes(self) -> dict[str, list[dict[str, Any]]]:
        """Get all RPC nodes grouped by blockchain using ORM"""
        all_nodes = self.db.repos.rpc_nodes.get_all_nodes()
        
        grouped_nodes = {}
        for node in all_nodes:
            blockchain = node.blockchain
            if blockchain not in grouped_nodes:
                grouped_nodes[blockchain] = []
            
            grouped_nodes[blockchain].append({
                'identifier': node.identifier,
                'name': node.name,
                'endpoint': node.endpoint,
                'owned': node.owned,
                'active': node.active,
                'weight': node.weight,
            })
        
        # Sort by weight within each blockchain
        for blockchain in grouped_nodes:
            grouped_nodes[blockchain].sort(
                key=lambda x: float(x['weight']),
                reverse=True,
            )
        
        return grouped_nodes
    
    def set_node_active_status(
            self,
            identifier: str,
            active: bool,
    ) -> bool:
        """Set the active status of a node using ORM"""
        return self.update_node(identifier=identifier, active=active)
    
    def validate_node_endpoint(self, endpoint: str) -> bool:
        """Validate that an endpoint URL is properly formatted"""
        # Basic validation
        if not endpoint.startswith(('http://', 'https://', 'ws://', 'wss://')):
            return False
        
        # TODO: Additional validation could include:
        # TODO: - Checking URL format
        # TODO: - Testing actual connectivity
        # TODO: - Verifying it's an EVM RPC endpoint
        
        return True
    
    def export_nodes_configuration(self) -> dict[str, Any]:
        """Export all nodes configuration for backup using ORM"""
        return {
            'version': 1,
            'nodes': self.get_all_nodes(),
            'exported_at': Timestamp(int(time.time())),
        }
    
    def import_nodes_configuration(
            self,
            config: dict[str, Any],
            overwrite: bool = False,
    ) -> int:
        """Import nodes configuration from backup using ORM
        
        Returns number of nodes imported
        """
        if config.get('version') != 1:
            raise ValueError("Unsupported configuration version")
        
        imported_count = 0
        
        with self.db.repos.unit_of_work():
            for blockchain, nodes in config.get('nodes', {}).items():
                for node_data in nodes:
                    # Skip non-owned nodes unless overwriting
                    if not node_data['owned'] and not overwrite:
                        continue
                    
                    # Check if node exists
                    existing = self.db.repos.rpc_nodes.get_node(node_data['identifier'])
                    
                    if existing and not overwrite:
                        continue
                    
                    if existing:
                        # Update existing
                        self.db.repos.rpc_nodes.update_node(
                            identifier=node_data['identifier'],
                            name=node_data['name'],
                            endpoint=node_data['endpoint'],
                            active=node_data['active'],
                            weight=node_data['weight'],
                        )
                    else:
                        # Add new
                        self.db.repos.rpc_nodes.add_node(
                            identifier=node_data['identifier'],
                            name=node_data['name'],
                            endpoint=node_data['endpoint'],
                            owned=node_data['owned'],
                            active=node_data['active'],
                            weight=node_data['weight'],
                            blockchain=blockchain,
                        )
                    
                    imported_count += 1
        
        log.info(f"Imported {imported_count} RPC nodes")
        return imported_count