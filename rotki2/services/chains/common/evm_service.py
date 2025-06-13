"""Base service for EVM-compatible blockchains."""
import logging
from abc import ABC, abstractmethod
from typing import Any

from rotki2.common.types import ChecksumEvmAddress, EvmTokenKind
from rotki2.db.models.user.evm import EvmTransaction

logger = logging.getLogger(__name__)


class BaseEvmService(ABC):
    """
    Base service class for EVM-compatible blockchains.
    
    This class provides common functionality shared across all EVM chains,
    including balance queries, transaction handling, and token operations.
    """
    
    def __init__(self, chain_id: int, chain_name: str) -> None:
        """
        Initialize the base EVM service.
        
        Args:
            chain_id: The chain ID for this EVM network
            chain_name: Human-readable name of the chain
        """
        self.chain_id = chain_id
        self.chain_name = chain_name
        logger.info(f"Initializing {chain_name} service (chain_id: {chain_id})")
    
    @abstractmethod
    async def get_native_balance(self, address: ChecksumEvmAddress) -> str:
        """
        Get the native token balance for an address.
        
        Args:
            address: The address to query
            
        Returns:
            Balance as a string in wei
        """
        ...
    
    @abstractmethod
    async def get_token_balance(
        self,
        token_address: ChecksumEvmAddress,
        account_address: ChecksumEvmAddress,
    ) -> str:
        """
        Get the token balance for an address.
        
        Args:
            token_address: The token contract address
            account_address: The account to query
            
        Returns:
            Balance as a string in the token's smallest unit
        """
        ...
    
    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> EvmTransaction | None:
        """
        Get transaction details by hash.
        
        Args:
            tx_hash: The transaction hash
            
        Returns:
            Transaction details or None if not found
        """
        ...
    
    @abstractmethod
    async def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any] | None:
        """
        Get transaction receipt by hash.
        
        Args:
            tx_hash: The transaction hash
            
        Returns:
            Transaction receipt or None if not found
        """
        ...
    
    @abstractmethod
    async def get_logs(
        self,
        from_block: int,
        to_block: int | str,
        address: ChecksumEvmAddress | None = None,
        topics: list[str | None] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get logs/events from the blockchain.
        
        Args:
            from_block: Starting block number
            to_block: Ending block number or 'latest'
            address: Contract address to filter logs (optional)
            topics: Topic filters (optional)
            
        Returns:
            List of log entries
        """
        ...
    
    @abstractmethod
    async def get_token_info(
        self,
        token_address: ChecksumEvmAddress,
        token_kind: EvmTokenKind,
    ) -> dict[str, Any]:
        """
        Get token information (name, symbol, decimals, etc).
        
        Args:
            token_address: The token contract address
            token_kind: Type of token (ERC20, ERC721, etc)
            
        Returns:
            Dictionary with token information
        """
        ...
    
    @abstractmethod
    async def multicall(
        self,
        calls: list[tuple[ChecksumEvmAddress, bytes]],
        block_number: int | str = "latest",
    ) -> list[bytes]:
        """
        Execute multiple contract calls in a single request.
        
        Args:
            calls: List of (contract_address, encoded_call_data) tuples
            block_number: Block number to execute calls at
            
        Returns:
            List of encoded results
        """
        ...
    
    async def get_block_by_timestamp(self, timestamp: int) -> int | None:
        """
        Get the closest block number to a given timestamp.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            Block number or None if not found
        """
        # Default implementation - can be overridden by specific chains
        # This is a placeholder that should be implemented with binary search
        logger.warning(f"get_block_by_timestamp not implemented for {self.chain_name}")
        return None
    
    async def detect_tokens_for_address(
        self,
        address: ChecksumEvmAddress,
        token_chunks: list[list[ChecksumEvmAddress]] | None = None,
    ) -> list[ChecksumEvmAddress]:
        """
        Detect which tokens an address has interacted with.
        
        Args:
            address: The address to check
            token_chunks: Optional list of token addresses to check in batches
            
        Returns:
            List of token addresses that the account has balance in
        """
        # Default implementation - can be overridden
        logger.warning(f"detect_tokens_for_address not implemented for {self.chain_name}")
        return []
    
    def __repr__(self) -> str:
        """String representation of the service."""
        return f"<{self.__class__.__name__}(chain_id={self.chain_id}, chain_name='{self.chain_name}')>"