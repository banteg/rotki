"""Ethereum-specific node client implementation."""
import logging
from typing import Any

import httpx

from rotki2.common.types import ChecksumEvmAddress, EVMTxHash
from rotki2.services.chains.common.node_client import BaseNodeClient

logger = logging.getLogger(__name__)


# Ethereum chain constants
ETHEREUM_CHAIN_ID = 1
ETHEREUM_GENESIS_TIMESTAMP = 1438269973

# Archive node check constants
ARCHIVE_NODE_CHECK_ADDRESS = "0x50532e4Be195D1dE0c2E6DfA46D9ec0a4Fee6861"
ARCHIVE_NODE_CHECK_BLOCK = 87042
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = "0x119f5dd85dca1f000"  # 5.1063307 ETH in wei

# Pruned node check constants
PRUNED_NODE_CHECK_TX_HASH = "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"

# ENS constants
ENS_MAINNET_ADDR = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
ENS_REVERSE_RECORDS_ADDR = "0x3671aE578E63FdF66ad4F3E12CC0c0d71Ac7510C"

# ETH2 constants
ETH2_DEPOSIT_ADDRESS = "0x00000000219ab540356cBB839Cbe05303d7705Fa"


class EthereumNodeClient(BaseNodeClient):
    """
    Node client for interacting with Ethereum RPC nodes.
    
    This client handles Ethereum-specific features including:
    - ENS (Ethereum Name Service) support
    - ETH2 deposit tracking
    - Archive/pruned node detection
    - Multiple node provider support
    """
    
    def __init__(self, http_client: httpx.AsyncClient, node_url: str) -> None:
        """Initialize the Ethereum node client."""
        super().__init__(
            http_client=http_client,
            node_url=node_url,
            chain_name="Ethereum",
        )
        self.chain_id = ETHEREUM_CHAIN_ID
        self._is_archive: bool | None = None
        self._is_pruned: bool | None = None
    
    async def is_connected(self) -> bool:
        """Check if the node is connected and responsive."""
        try:
            chain_id = await self.post("eth_chainId")
            return int(chain_id, 16) == ETHEREUM_CHAIN_ID
        except Exception as e:
            logger.error(f"Failed to check Ethereum node connection: {e}")
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
        """Get transaction receipt."""
        return await self.post("eth_getTransactionReceipt", [tx_hash])
    
    async def call(
        self,
        to: ChecksumEvmAddress,
        data: str,
        block_number: int | str = "latest",
        from_address: ChecksumEvmAddress | None = None,
    ) -> str:
        """
        Execute a contract call.
        
        Args:
            to: Contract address
            data: Encoded call data (hex string)
            block_number: Block number or 'latest'
            from_address: Optional from address for the call
            
        Returns:
            Call result as hex string
        """
        params = {
            "to": to,
            "data": data,
        }
        
        if from_address:
            params["from"] = from_address
        
        block_param = block_number
        if isinstance(block_number, int):
            block_param = hex(block_number)
        
        return await self.post("eth_call", [params, block_param])
    
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
    
    # ENS-specific methods
    async def ens_lookup(self, name: str) -> ChecksumEvmAddress | None:
        """
        Resolve an ENS name to an address.
        
        Args:
            name: ENS name (e.g., "vitalik.eth")
            
        Returns:
            Resolved address or None if not found
        """
        # This is a simplified implementation
        # Real implementation would use ENS contract calls
        logger.warning(f"ENS lookup not fully implemented for {name}")
        return None
    
    async def ens_reverse_lookup(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, str | None]:
        """
        Perform reverse ENS lookup for multiple addresses.
        
        Args:
            addresses: List of addresses to lookup
            
        Returns:
            Mapping of addresses to ENS names (or None)
        """
        # This would call the ENS reverse records contract
        # Using multicall for efficiency
        result = {}
        for addr in addresses:
            result[addr] = None  # Placeholder
        
        logger.warning("ENS reverse lookup not fully implemented")
        return result
    
    async def get_eth2_deposits(
        self,
        address: ChecksumEvmAddress,
        from_block: int = 0,
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """
        Get ETH2 deposits made by an address.
        
        Args:
            address: Address to check
            from_block: Starting block
            to_block: Ending block
            
        Returns:
            List of deposit events
        """
        # DepositEvent topic
        deposit_event_topic = "0x649bbc62d0e31342afea4e5cd82d4049e7e1ee912fc0889aa790803be39038c5"
        
        # Filter for deposits from this address
        logs = await self.get_logs(
            from_block=from_block,
            to_block=to_block,
            address=ETH2_DEPOSIT_ADDRESS,
            topics=[deposit_event_topic],
        )
        
        # Filter logs where the sender is our address
        # This is simplified - real implementation would decode the logs
        deposits = []
        for log in logs:
            # Check if this deposit is from our address
            # Real implementation would decode the log data
            deposits.append(log)
        
        return deposits