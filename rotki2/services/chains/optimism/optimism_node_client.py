"""Optimism-specific node client implementation."""
import logging
from typing import Any

import httpx

from rotki2.common.types import ChecksumEvmAddress, EvmTokenKind, EVMTxHash
from rotki2.services.chains.common.node_client import BaseNodeClient

logger = logging.getLogger(__name__)


# Optimism chain constants
OPTIMISM_CHAIN_ID = 10
OPTIMISM_GENESIS_TIMESTAMP = 1636666246

# Archive node check constants
ARCHIVE_NODE_CHECK_ADDRESS = "0x76a05Df20bFEF5EcE3eB16afF9cb10134199A921"
ARCHIVE_NODE_CHECK_BLOCK = 74000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = "0x0b1a2bc2ec50000"  # 0.05 ETH in wei

# Pruned node check constants  
PRUNED_NODE_CHECK_TX_HASH = "0x5e77a04531c7c107af1882d76cbff9486d0a9aa53701c30888509d4f5f2b003a"


class OptimismNodeClient(BaseNodeClient):
    """
    Node client for interacting with Optimism RPC nodes.
    
    This client handles Optimism-specific features including:
    - L1 fee information in receipts
    - Archive/pruned node detection
    - Optimism-specific contract addresses
    """
    
    def __init__(self, http_client: httpx.AsyncClient, node_url: str) -> None:
        """Initialize the Optimism node client."""
        super().__init__(
            http_client=http_client,
            node_url=node_url,
            chain_name="Optimism",
        )
        self.chain_id = OPTIMISM_CHAIN_ID
        self._is_archive: bool | None = None
        self._is_pruned: bool | None = None
    
    async def is_connected(self) -> bool:
        """Check if the node is connected and responsive."""
        try:
            chain_id = await self.post("eth_chainId")
            return int(chain_id, 16) == OPTIMISM_CHAIN_ID
        except Exception as e:
            logger.error(f"Failed to check Optimism node connection: {e}")
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
        Get ETH balance for an address.
        
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
        """
        Get transaction receipt with Optimism-specific fields.
        
        Optimism receipts include additional L1 fee information.
        """
        result = await self.post("eth_getTransactionReceipt", [tx_hash])
        
        if result and "l1Fee" in result:
            # Ensure l1Fee is properly formatted
            result["l1Fee"] = result["l1Fee"]
            
        return result
    
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
    
    async def estimate_gas(
        self,
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress | None,
        value: str = "0x0",
        data: str = "0x",
    ) -> str:
        """
        Estimate gas for a transaction.
        
        Returns:
            Estimated gas as hex string
        """
        params = {
            "from": from_address,
            "value": value,
            "data": data,
        }
        
        if to_address:
            params["to"] = to_address
        
        return await self.post("eth_estimateGas", [params])
    
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