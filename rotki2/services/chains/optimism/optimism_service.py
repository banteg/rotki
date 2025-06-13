"""Optimism blockchain service implementation."""
import logging
from decimal import Decimal
from typing import Any

from rotki2.common.types import ChecksumEvmAddress, EvmTokenKind, EVMTxHash
from rotki2.db.models.user.evm import EvmTransaction
from rotki2.db.repositories.optimism_repository import OptimismRepository
from rotki2.services.chains.common.decoding_service import DecodingService
from rotki2.services.chains.common.evm_service import BaseEvmService
from rotki2.services.chains.optimism.optimism_node_client import OptimismNodeClient

logger = logging.getLogger(__name__)


# Common contract addresses on Optimism
OPTIMISM_CONTRACTS = {
    "multicall": "0x2DC0E2aa608532Da689e89e237dF582B783E552C",
    "balance_scanner": "0x9e5076DF494FC949aBc4461F4E57592B81517D81",
    "dsproxy_registry": "0x283Cc5C26e53D66ed2Ea252D986F094B37E6e895",
}


class OptimismService(BaseEvmService):
    """
    Service for interacting with the Optimism blockchain.
    
    Handles all Optimism-specific business logic including:
    - Balance queries with L1 fee calculations
    - Transaction processing and decoding
    - Token operations
    - Chain-specific features
    """
    
    def __init__(
        self,
        node_client: OptimismNodeClient,
        repository: OptimismRepository,
        decoding_service: DecodingService | None = None,
    ) -> None:
        """
        Initialize the Optimism service.
        
        Args:
            node_client: Client for RPC node communication
            repository: Repository for database operations
            decoding_service: Optional decoding service for transactions
        """
        super().__init__(chain_id=10, chain_name="Optimism")
        self.node_client = node_client
        self.repository = repository
        self.decoding_service = decoding_service
        
        logger.info("Initialized Optimism service")
    
    async def get_native_balance(self, address: ChecksumEvmAddress) -> str:
        """Get ETH balance for an address."""
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
        
        # Save to database
        return await self.repository.save_transaction(tx_data)
    
    async def get_transaction_receipt(self, tx_hash: EVMTxHash) -> dict[str, Any] | None:
        """Get transaction receipt with L1 fee information."""
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
                "l1Fee": receipt.extra_data.get("l1_fee") if receipt.extra_data else None,
            }
        
        # Query from node
        receipt_data = await self.node_client.get_transaction_receipt(tx_hash)
        if not receipt_data:
            return None
        
        # Extract L1 fee if present
        l1_fee = receipt_data.get("l1Fee")
        
        # Save to database
        await self.repository.save_receipt(receipt_data, l1_fee)
        
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
        multicall_address = OPTIMISM_CONTRACTS["multicall"]
        
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
    
    async def get_balances_for_addresses(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, str]:
        """
        Get ETH balances for multiple addresses efficiently.
        
        Args:
            addresses: List of addresses to query
            
        Returns:
            Dictionary mapping addresses to balances in wei
        """
        if not addresses:
            return {}
        
        # Use balance scanner contract for efficiency
        scanner_address = OPTIMISM_CONTRACTS["balance_scanner"]
        
        # ether_balances function signature
        method_sig = "0xdbdbb51b"  # ether_balances(address[])
        
        # Encode addresses array (simplified)
        encoded_addresses = ""
        for addr in addresses:
            encoded_addresses += addr[2:].zfill(64)
        
        data = method_sig + encoded_addresses
        
        try:
            result = await self.node_client.call(scanner_address, data)
            
            # Decode results (simplified - real implementation would use eth_abi)
            balances = {}
            # Each balance is 32 bytes
            for i, addr in enumerate(addresses):
                start = 2 + (i * 64)  # Skip 0x prefix
                end = start + 64
                balance_hex = result[start:end] if len(result) > end else "0x0"
                balances[addr] = str(int(balance_hex, 16))
            
            return balances
            
        except Exception as e:
            logger.error(f"Failed to get balances using scanner: {e}")
            # Fallback to individual queries
            balances = {}
            for addr in addresses:
                try:
                    balance = await self.get_native_balance(addr)
                    balances[addr] = balance
                except Exception as e:
                    logger.error(f"Failed to get balance for {addr}: {e}")
                    balances[addr] = "0"
            
            return balances
    
    async def decode_transaction(
        self,
        tx_hash: EVMTxHash,
    ) -> dict[str, Any]:
        """
        Decode a transaction using the decoding service.
        
        Args:
            tx_hash: Transaction hash to decode
            
        Returns:
            Decoded transaction data
        """
        if not self.decoding_service:
            return {
                "tx_hash": tx_hash,
                "decoded": False,
                "error": "No decoding service configured",
            }
        
        # Get transaction and receipt
        tx_data = await self.node_client.get_transaction_by_hash(tx_hash)
        if not tx_data:
            return {
                "tx_hash": tx_hash,
                "decoded": False,
                "error": "Transaction not found",
            }
        
        receipt_data = await self.node_client.get_transaction_receipt(tx_hash)
        if not receipt_data:
            return {
                "tx_hash": tx_hash,
                "decoded": False,
                "error": "Receipt not found",
            }
        
        # Get logs
        logs = receipt_data.get("logs", [])
        
        # Decode
        result = await self.decoding_service.decode_transaction(
            tx_data=tx_data,
            receipt_data=receipt_data,
            logs=logs,
        )
        
        return {
            "tx_hash": tx_hash,
            "decoded": result.status.value == "decoded",
            "events": [event.model_dump() for event in result.events],
            "error": result.error,
        }
    
    async def get_total_cost(
        self,
        tx_hash: EVMTxHash,
    ) -> dict[str, str]:
        """
        Calculate total transaction cost including L1 fees.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Dictionary with l2_cost, l1_cost, and total_cost in wei
        """
        receipt = await self.get_transaction_receipt(tx_hash)
        if not receipt:
            raise ValueError(f"Receipt not found for {tx_hash}")
        
        tx = await self.get_transaction(tx_hash)
        if not tx:
            raise ValueError(f"Transaction not found for {tx_hash}")
        
        # Calculate L2 cost
        gas_used = Decimal(receipt["gasUsed"])
        gas_price = Decimal(tx.gas_price) if tx.gas_price else Decimal(0)
        l2_cost = gas_used * gas_price
        
        # Get L1 cost
        l1_cost = Decimal(receipt.get("l1Fee", 0))
        
        # Total cost
        total_cost = l2_cost + l1_cost
        
        return {
            "l2_cost": str(l2_cost),
            "l1_cost": str(l1_cost),
            "total_cost": str(total_cost),
        }
    
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