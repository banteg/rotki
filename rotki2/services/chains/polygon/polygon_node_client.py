"""Polygon PoS-specific node client implementation."""
import logging
from typing import Any

import httpx

from rotki2.common.types import ChecksumEvmAddress, EVMTxHash
from rotki2.services.chains.common.node_client import BaseNodeClient

logger = logging.getLogger(__name__)


# Polygon PoS chain constants
POLYGON_CHAIN_ID = 137
POLYGON_GENESIS_TIMESTAMP = 1590824836
POLYGON_POL_HARDFORK_TIMESTAMP = 1725451200

# Archive node check constants
ARCHIVE_NODE_CHECK_ADDRESS = "0xc3F60BC338E0Af8f46F52650C813FBD3C071E165"
ARCHIVE_NODE_CHECK_BLOCK = 447
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = "0x15"  # 0.000000000000000021 MATIC in wei

# Pruned node check constants
PRUNED_NODE_CHECK_TX_HASH = "0xf6c3feac09aa84558510f74af0c9bf7fd51ff15f902f68d51592e09cad8896b2"


class PolygonNodeClient(BaseNodeClient):
    """
    Node client for interacting with Polygon PoS RPC nodes.
    
    This client handles Polygon-specific features including:
    - MATIC to POL token migration tracking
    - Archive/pruned node detection
    - Polygon-specific contract addresses
    """
    
    def __init__(self, http_client: httpx.AsyncClient, node_url: str) -> None:
        """Initialize the Polygon node client."""
        super().__init__(
            http_client=http_client,
            node_url=node_url,
            chain_name="Polygon PoS",
        )
        self.chain_id = POLYGON_CHAIN_ID
        self._is_archive: bool | None = None
        self._is_pruned: bool | None = None
    
    async def is_connected(self) -> bool:
        """Check if the node is connected and responsive."""
        try:
            chain_id = await self.post("eth_chainId")
            return int(chain_id, 16) == POLYGON_CHAIN_ID
        except Exception as e:
            logger.error(f"Failed to check Polygon node connection: {e}")
            return False
    
    async def get_block_number(self) -> int:
        """Get the current block number."""
        result = await self.post("eth_blockNumber")
        return int(result, 16)
    
    async def get_balance(
        self,
        address: ChecksumEvmAddress,
        block_number: int | str = "latest",
    ) -> str:
        """
        Get MATIC/POL balance for an address.
        
        Args:
            address: The address to query
            block_number: Block number or 'latest'
            
        Returns:
            Balance in wei as hex string
        """
        params = [address, block_number]
        if isinstance(block_number, int):
            params[1] = hex(block_number)
        
        return await self.post("eth_getBalance", params)
    
    async def get_transaction_receipt(self, tx_hash: EVMTxHash) -> dict[str, Any] | None:
        """Get transaction receipt."""
        return await self.post("eth_getTransactionReceipt", [tx_hash])
    
    async def call(
        self,
        to: ChecksumEvmAddress,
        data: str,
        block_number: int | str = "latest",
    ) -> str:
        """
        Execute a contract call.
        
        Args:
            to: Contract address
            data: Encoded call data (hex string)
            block_number: Block number or 'latest'
            
        Returns:
            Call result as hex string
        """
        params = [
            {
                "to": to,
                "data": data,
            },
            block_number,
        ]
        
        if isinstance(block_number, int):
            params[1] = hex(block_number)
        
        return await self.post("eth_call", params)
    
    async def get_logs(
        self,
        from_block: int,
        to_block: int | str,
        address: ChecksumEvmAddress | list[ChecksumEvmAddress] | None = None,
        topics: list[str | None] | None = None,
    ) -> list[dict[str, Any]]:
        """Get logs/events from the blockchain."""
        params = {
            "fromBlock": hex(from_block),
            "toBlock": to_block if to_block == "latest" else hex(to_block),
        }
        
        if address is not None:
            params["address"] = address
        
        if topics is not None:
            params["topics"] = topics
        
        return await self.post("eth_getLogs", [params])
    
    async def is_archive_node(self) -> bool:
        """
        Check if this is an archive node.
        
        Archive nodes can query historical state at any block.
        """
        if self._is_archive is not None:
            return self._is_archive
        
        try:
            # Try to get balance at a specific historical block
            balance = await self.get_balance(
                ARCHIVE_NODE_CHECK_ADDRESS,
                ARCHIVE_NODE_CHECK_BLOCK,
            )
            
            # Check if the balance matches expected
            self._is_archive = balance == ARCHIVE_NODE_CHECK_EXPECTED_BALANCE
            
        except Exception as e:
            logger.debug(f"Archive node check failed: {e}")
            self._is_archive = False
        
        return self._is_archive
    
    async def is_pruned_node(self) -> bool:
        """
        Check if this is a pruned node.
        
        Pruned nodes cannot retrieve old transactions/receipts.
        """
        if self._is_pruned is not None:
            return self._is_pruned
        
        try:
            # Try to get an old transaction
            tx = await self.post("eth_getTransactionByHash", [PRUNED_NODE_CHECK_TX_HASH])
            self._is_pruned = tx is None
            
        except Exception as e:
            logger.debug(f"Pruned node check failed: {e}")
            # If we can't check, assume it's not pruned
            self._is_pruned = False
        
        return self._is_pruned
    
    async def get_transaction_by_hash(self, tx_hash: EVMTxHash) -> dict[str, Any] | None:
        """Get transaction details by hash."""
        return await self.post("eth_getTransactionByHash", [tx_hash])
    
    async def get_block_by_number(
        self,
        block_number: int | str,
        full_transactions: bool = False,
    ) -> dict[str, Any] | None:
        """Get block details by number."""
        params = [
            block_number if block_number == "latest" else hex(block_number),
            full_transactions,
        ]
        
        return await self.post("eth_getBlockByNumber", params)
    
    async def get_block_timestamp(self, block_number: int) -> int | None:
        """
        Get timestamp for a specific block.
        
        Args:
            block_number: Block number
            
        Returns:
            Unix timestamp or None if block not found
        """
        block = await self.get_block_by_number(block_number)
        if block and "timestamp" in block:
            return int(block["timestamp"], 16)
        return None
    
    def is_pol_hardfork_block(self, timestamp: int) -> bool:
        """
        Check if a timestamp is after the POL hardfork.
        
        After this timestamp, MATIC was renamed to POL.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            True if after POL hardfork
        """
        return timestamp >= POLYGON_POL_HARDFORK_TIMESTAMP