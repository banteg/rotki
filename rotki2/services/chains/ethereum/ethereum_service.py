"""Ethereum blockchain service implementation."""
import logging
from decimal import Decimal
from typing import Any

from rotki2.common.types import ChecksumEvmAddress, EvmTokenKind, EVMTxHash
from rotki2.db.models.user.evm import EvmTransaction
from rotki2.db.repositories.ethereum_repository import EthereumRepository
from rotki2.services.chains.common.decoding_service import DecodingService
from rotki2.services.chains.common.evm_service import BaseEvmService
from rotki2.services.chains.ethereum.ethereum_node_client import EthereumNodeClient

logger = logging.getLogger(__name__)


# Common contract addresses on Ethereum
ETHEREUM_CONTRACTS = {
    "multicall": "0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696",
    "balance_scanner": "0x9e5076DF494FC949aBc4461F4E57592B81517D81",
    "dsproxy_registry": "0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4",
    "ens_registry": "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e",
    "ens_reverse_records": "0x3671aE578E63FdF66ad4F3E12CC0c0d71Ac7510C",
}


class EthereumService(BaseEvmService):
    """
    Service for interacting with the Ethereum blockchain.
    
    Handles all Ethereum-specific business logic including:
    - ENS (Ethereum Name Service) operations
    - ETH2 deposit tracking
    - Balance queries
    - Transaction processing and decoding
    - Integration with multiple node providers
    """
    
    def __init__(
        self,
        node_client: EthereumNodeClient,
        repository: EthereumRepository,
        decoding_service: DecodingService | None = None,
    ) -> None:
        """
        Initialize the Ethereum service.
        
        Args:
            node_client: Client for RPC node communication
            repository: Repository for database operations
            decoding_service: Optional decoding service for transactions
        """
        super().__init__(chain_id=1, chain_name="Ethereum")
        self.node_client = node_client
        self.repository = repository
        self.decoding_service = decoding_service
        
        logger.info("Initialized Ethereum service")
    
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
        multicall_address = ETHEREUM_CONTRACTS["multicall"]
        
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
    
    # ENS-specific methods
    async def ens_lookup(self, name: str) -> ChecksumEvmAddress | None:
        """
        Resolve an ENS name to an address.
        
        Args:
            name: ENS name (e.g., "vitalik.eth")
            
        Returns:
            Resolved address or None if not found
        """
        return await self.node_client.ens_lookup(name)
    
    async def ens_reverse_lookup(
        self,
        addresses: list[ChecksumEvmAddress],
        use_cache: bool = True,
    ) -> dict[ChecksumEvmAddress, str | None]:
        """
        Perform reverse ENS lookup for multiple addresses.
        
        Args:
            addresses: List of addresses to lookup
            use_cache: Whether to use cached ENS names
            
        Returns:
            Mapping of addresses to ENS names (or None)
        """
        if not addresses:
            return {}
        
        result = {}
        
        # Check cache first if enabled
        if use_cache:
            cached_names = await self.repository.get_ens_mappings_batch(addresses)
            result.update(cached_names)
            
            # Filter out addresses we already have names for
            addresses_to_query = [
                addr for addr in addresses
                if addr not in cached_names or cached_names[addr] is None
            ]
        else:
            addresses_to_query = addresses
        
        # Query remaining addresses
        if addresses_to_query:
            fresh_names = await self.node_client.ens_reverse_lookup(addresses_to_query)
            
            # Save to cache
            for addr, name in fresh_names.items():
                if name:
                    await self.repository.save_ens_mapping(addr, name)
                result[addr] = name
        
        return result
    
    # ETH2-specific methods
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
            List of deposit information
        """
        # Check database first
        db_deposits = await self.repository.get_eth2_deposits(depositor=address)
        
        # Get latest deposit block from DB to avoid re-querying
        latest_db_block = 0
        if db_deposits:
            latest_db_block = max(d.block_number for d in db_deposits)
        
        # Query new deposits from node
        query_from_block = max(from_block, latest_db_block + 1)
        
        if query_from_block <= (to_block if isinstance(to_block, int) else float('inf')):
            new_deposits = await self.node_client.get_eth2_deposits(
                address=address,
                from_block=query_from_block,
                to_block=to_block,
            )
            
            # Process and save new deposits
            for deposit_log in new_deposits:
                # Decode deposit data (simplified)
                # Real implementation would properly decode the log
                await self.repository.save_eth2_deposit(
                    tx_hash=deposit_log["transactionHash"],
                    from_address=address,
                    pubkey="",  # Would be decoded from log
                    withdrawal_credentials="",  # Would be decoded
                    amount="32000000000000000000",  # 32 ETH standard
                    signature="",  # Would be decoded
                    deposit_index=0,  # Would be decoded
                    block_number=int(deposit_log["blockNumber"], 16),
                    timestamp=0,  # Would need block timestamp
                )
        
        # Return all deposits
        all_deposits = []
        for deposit in await self.repository.get_eth2_deposits(depositor=address):
            all_deposits.append({
                "tx_hash": deposit.tx_hash,
                "from_address": deposit.from_address,
                "pubkey": deposit.pubkey,
                "amount": deposit.amount,
                "block_number": deposit.block_number,
                "timestamp": deposit.timestamp,
                "validator_index": deposit.validator_index,
            })
        
        return all_deposits
    
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
        scanner_address = ETHEREUM_CONTRACTS["balance_scanner"]
        
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