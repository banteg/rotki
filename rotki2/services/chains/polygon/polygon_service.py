"""Polygon PoS blockchain service implementation."""
import logging
from typing import Any

from rotki2.common.types import ChecksumEvmAddress, EvmTokenKind, EVMTxHash
from rotki2.db.models.user.evm import EvmTransaction
from rotki2.db.repositories.polygon_repository import PolygonRepository
from rotki2.services.chains.common.decoding_service import DecodingService
from rotki2.services.chains.common.evm_service import BaseEvmService
from rotki2.services.chains.polygon.polygon_node_client import PolygonNodeClient

logger = logging.getLogger(__name__)


# Common contract addresses on Polygon
POLYGON_CONTRACTS = {
    "multicall": "0x275617327c958bD06b5D6b871E7f491D76113dd8",
    "balance_scanner": "0x9e5076DF494FC949aBc4461F4E57592B81517D81",
    # Polygon PoS Bridge contracts
    "root_chain_manager": "0xA0c68C638235ee32657e8f720a23ceC1bFc77C77",
    "erc20_predicate": "0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf",
}


class PolygonService(BaseEvmService):
    """
    Service for interacting with the Polygon PoS blockchain.
    
    Handles all Polygon-specific business logic including:
    - Balance queries with MATIC/POL naming
    - Bridge transaction handling
    - Transaction processing and decoding
    - Token operations
    """
    
    def __init__(
        self,
        node_client: PolygonNodeClient,
        repository: PolygonRepository,
        decoding_service: DecodingService | None = None,
    ) -> None:
        """
        Initialize the Polygon service.
        
        Args:
            node_client: Client for RPC node communication
            repository: Repository for database operations
            decoding_service: Optional decoding service for transactions
        """
        super().__init__(chain_id=137, chain_name="Polygon PoS")
        self.node_client = node_client
        self.repository = repository
        self.decoding_service = decoding_service
        
        logger.info("Initialized Polygon PoS service")
    
    async def get_native_balance(self, address: ChecksumEvmAddress) -> str:
        """Get MATIC/POL balance for an address."""
        balance_hex = await self.node_client.get_balance(address)
        return str(int(balance_hex, 16))
    
    async def get_token_balance(
        self,
        token_address: ChecksumEvmAddress,
        account_address: ChecksumEvmAddress,
    ) -> str:
        """Get ERC20 token balance for an address."""
        # ERC20 balanceOf method signature
        method_signature = "0x70a08231"
        # Pad address to 32 bytes
        padded_address = account_address[2:].zfill(64)
        data = method_signature + padded_address
        
        result = await self.node_client.call(token_address, data)
        return str(int(result, 16))
    
    async def get_transaction(self, tx_hash: EVMTxHash) -> EvmTransaction | None:
        """Get transaction details by hash."""
        # First check database
        tx = await self.repository.get_transaction(tx_hash)
        if tx:
            return tx
        
        # Query from node
        tx_data = await self.node_client.get_transaction_by_hash(tx_hash)
        if not tx_data:
            return None
        
        # Get block timestamp for POL naming
        block_number = int(tx_data["blockNumber"], 16)
        timestamp = await self.node_client.get_block_timestamp(block_number)
        if timestamp:
            tx_data["timestamp"] = timestamp
        
        # Save to database
        return await self.repository.save_transaction(tx_data)
    
    async def get_transaction_receipt(self, tx_hash: EVMTxHash) -> dict[str, Any] | None:
        """Get transaction receipt."""
        # First check database
        receipt = await self.repository.get_receipt(tx_hash)
        if receipt:
            return {
                "transactionHash": receipt.tx_hash,
                "contractAddress": receipt.contract_address,
                "gasUsed": receipt.gas_used,
                "cumulativeGasUsed": receipt.cumulative_gas_used,
                "logs": receipt.logs,
                "status": receipt.status,
            }
        
        # Query from node
        receipt_data = await self.node_client.get_transaction_receipt(tx_hash)
        if not receipt_data:
            return None
        
        # Save to database
        await self.repository.save_receipt(receipt_data)
        
        return receipt_data
    
    async def get_logs(
        self,
        from_block: int,
        to_block: int | str,
        address: ChecksumEvmAddress | None = None,
        topics: list[str | None] | None = None,
    ) -> list[dict[str, Any]]:
        """Get logs from the blockchain."""
        return await self.node_client.get_logs(
            from_block=from_block,
            to_block=to_block,
            address=address,
            topics=topics,
        )
    
    async def get_token_info(
        self,
        token_address: ChecksumEvmAddress,
        token_kind: EvmTokenKind,
    ) -> dict[str, Any]:
        """Get token information."""
        if token_kind == EvmTokenKind.ERC20:
            # Get name, symbol, decimals
            calls = [
                (token_address, "0x06fdde03"),  # name()
                (token_address, "0x95d89b41"),  # symbol()
                (token_address, "0x313ce567"),  # decimals()
            ]
            
            results = []
            for address, data in calls:
                try:
                    result = await self.node_client.call(address, data)
                    results.append(result)
                except Exception:
                    results.append(None)
            
            # Decode results
            name = self._decode_string(results[0]) if results[0] else "Unknown"
            symbol = self._decode_string(results[1]) if results[1] else "???"
            decimals = int(results[2], 16) if results[2] else 18
            
            return {
                "name": name,
                "symbol": symbol,
                "decimals": decimals,
                "kind": token_kind,
            }
        
        elif token_kind == EvmTokenKind.ERC721:
            # Get name and symbol for NFT
            calls = [
                (token_address, "0x06fdde03"),  # name()
                (token_address, "0x95d89b41"),  # symbol()
            ]
            
            results = []
            for address, data in calls:
                try:
                    result = await self.node_client.call(address, data)
                    results.append(result)
                except Exception:
                    results.append(None)
            
            name = self._decode_string(results[0]) if results[0] else "Unknown NFT"
            symbol = self._decode_string(results[1]) if results[1] else "NFT"
            
            return {
                "name": name,
                "symbol": symbol,
                "kind": token_kind,
            }
        
        else:
            raise ValueError(f"Unsupported token kind: {token_kind}")
    
    async def multicall(
        self,
        calls: list[tuple[ChecksumEvmAddress, bytes]],
        block_number: int | str = "latest",
    ) -> list[bytes]:
        """Execute multiple calls using multicall contract."""
        # Encode multicall data
        multicall_address = POLYGON_CONTRACTS["multicall"]
        
        # Multicall aggregate function signature
        method_sig = "0x252dba42"  # aggregate((address,bytes)[])
        
        # Encode calls array
        # This is a simplified encoding - real implementation would use eth_abi
        encoded_calls = ""
        for target, calldata in calls:
            # Each call is (address, bytes)
            encoded_calls += target[2:].zfill(64)  # address
            encoded_calls += calldata.hex()  # bytes
        
        data = method_sig + encoded_calls
        
        result = await self.node_client.call(multicall_address, data, block_number)
        
        # Decode results - simplified
        # Real implementation would properly decode the aggregate return value
        return [bytes.fromhex(result[2:])]  # Placeholder
    
    async def get_native_token_name(self, timestamp: int | None = None) -> str:
        """
        Get the native token name based on timestamp.
        
        After the POL hardfork, MATIC was renamed to POL.
        
        Args:
            timestamp: Unix timestamp (uses current time if None)
            
        Returns:
            "MATIC" or "POL" depending on timestamp
        """
        if timestamp is None:
            # Get current block timestamp
            current_block = await self.node_client.get_block_number()
            timestamp = await self.node_client.get_block_timestamp(current_block) or 0
        
        return "POL" if self.node_client.is_pol_hardfork_block(timestamp) else "MATIC"
    
    async def get_bridge_deposits(
        self,
        address: ChecksumEvmAddress,
        from_block: int = 0,
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """
        Get bridge deposits from Ethereum to Polygon for an address.
        
        Args:
            address: Address to check
            from_block: Starting block
            to_block: Ending block
            
        Returns:
            List of bridge deposit events
        """
        # This would track LockedERC20 events on the Polygon bridge
        # Simplified implementation - real one would decode events properly
        bridge_topic = "0x9b217a401a5ddf7c4d474074aff9958a18d48690d77cc2151c4706aa7348b401"
        
        logs = await self.get_logs(
            from_block=from_block,
            to_block=to_block,
            address=POLYGON_CONTRACTS["erc20_predicate"],
            topics=[bridge_topic],
        )
        
        deposits = []
        for log in logs:
            # Decode and filter for our address
            # Real implementation would properly decode the log
            deposits.append({
                "tx_hash": log["transactionHash"],
                "block_number": int(log["blockNumber"], 16),
                "token": log["address"],
                "amount": "0",  # Would be decoded
                "from_address": address,
            })
        
        return deposits
    
    def _decode_string(self, hex_data: str) -> str:
        """Decode a string from hex data."""
        if not hex_data or hex_data == "0x":
            return ""
        
        # Remove 0x prefix
        data = hex_data[2:]
        
        # Simple string decoding - real implementation would use eth_abi
        try:
            # Skip offset and length (first 64 bytes each)
            if len(data) >= 128:
                string_data = data[128:]
                # Convert hex to bytes and decode
                return bytes.fromhex(string_data).decode("utf-8").strip("\x00")
        except Exception:
            pass
        
        return ""