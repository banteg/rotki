"""Generic EVM chain manager for all EVM-compatible chains."""
from typing import TYPE_CHECKING, Any

from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotki2.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotki2.chain.evm.tokens import EvmTokens
from rotki2.chain.evm.transactions import EvmTransactions

if TYPE_CHECKING:
    from rotki2.chain.evm.configs.base import ChainConfig
    from rotki2.db.database import DBConnection
    from rotki2.utils.messages import MessagesAggregator


class EvmChainManager:
    """A generic manager for any EVM-compatible chain."""
    
    def __init__(
        self,
        config: 'ChainConfig',
        database: 'DBConnection',
        msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.config = config
        self.database = database
        self.msg_aggregator = msg_aggregator
        
        # Initialize the chain-specific node inquirer
        self.node_inquirer = config.inquirer_class(
            database=database,
            msg_aggregator=msg_aggregator,
        )
        
        # Initialize generic EVM components
        self.tokens = EvmTokens(
            database=database,
            evm_inquirer=self.node_inquirer,
        )
        self.transactions = EvmTransactions(
            evm_inquirer=self.node_inquirer,
            database=database,
        )
        
        # Initialize protocol handlers from configuration
        self.protocol_handlers = [
            protocol_class(self.node_inquirer)
            for protocol_class in config.supported_protocols
        ]
        
        # Initialize transaction decoder with protocol handlers
        self.transactions_decoder = EVMTransactionDecoder(
            database=database,
            evm_inquirer=self.node_inquirer,
            protocol_handlers=self.protocol_handlers,
        )
        
        self._connected = False
    
    @property
    def chain_id(self) -> ChainID:
        """Get the chain ID."""
        return self.config.chain_id
    
    @property
    def blockchain(self) -> str:
        """Get the blockchain name."""
        return self.config.blockchain.value
    
    async def connect(self) -> None:
        """Connect to the chain's node."""
        if self._connected:
            return
        
        await self.node_inquirer.connect()
        self._connected = True
        self.msg_aggregator.add_message(
            f'Connected to {self.config.name} node',
            message_type='info',
        )
    
    async def disconnect(self) -> None:
        """Disconnect from the chain's node."""
        if not self._connected:
            return
        
        await self.node_inquirer.disconnect()
        self._connected = False
        self.msg_aggregator.add_message(
            f'Disconnected from {self.config.name} node',
            message_type='info',
        )
    
    async def get_native_balance(self, address: ChecksumEvmAddress) -> str:
        """Get native token balance for an address."""
        if not self._connected:
            await self.connect()
        
        balance = await self.node_inquirer.get_balance(address)
        return str(balance)
    
    async def get_token_balances(
        self,
        address: ChecksumEvmAddress,
        token_addresses: list[ChecksumEvmAddress] | None = None,
    ) -> dict[ChecksumEvmAddress, str]:
        """Get token balances for an address."""
        if not self._connected:
            await self.connect()
        
        return await self.tokens.get_balances(address, token_addresses)
    
    async def get_protocol_balances(self, address: ChecksumEvmAddress) -> dict[str, Any]:
        """Get protocol-specific balances for an address."""
        if not self._connected:
            await self.connect()
        
        all_balances = {}
        for handler in self.protocol_handlers:
            try:
                balances = await handler.get_balances(address)
                if balances:
                    all_balances[handler.get_protocol_name()] = balances
            except Exception as e:
                self.msg_aggregator.add_error(
                    f'Failed to get {handler.get_protocol_name()} balances on '
                    f'{self.config.name}: {str(e)}',
                )
        
        return all_balances
    
    async def get_transactions(
        self,
        address: ChecksumEvmAddress,
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get transactions for an address."""
        if not self._connected:
            await self.connect()
        
        return await self.transactions.get_transactions(
            address=address,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
    
    async def decode_transaction(self, tx_hash: str) -> dict[str, Any]:
        """Decode a transaction."""
        if not self._connected:
            await self.connect()
        
        return await self.transactions_decoder.decode_transaction(tx_hash)
    
    async def get_block_by_time(self, timestamp: int) -> int:
        """Get block number by timestamp."""
        if not self._connected:
            await self.connect()
        
        return await self.node_inquirer.get_blocknumber_by_time(timestamp)
    
    def __repr__(self) -> str:
        """String representation."""
        return f'<EvmChainManager {self.config.name} connected={self._connected}>'