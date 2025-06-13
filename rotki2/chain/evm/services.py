"""EVM chain services for interacting with blockchain nodes"""
import asyncio
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain

from rotki2.chain.optimism.node_inquirer import OptimismInquirer

if TYPE_CHECKING:
    from rotkehlchen.externalapis.etherscan import Etherscan

    from rotki2.api.v2.services.database import DatabaseService
    from rotki2.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)


class EvmChainService:
    """Service for interacting with EVM-compatible blockchains"""

    def __init__(
            self,
            database: 'DatabaseService',
            etherscan: 'Etherscan',
    ) -> None:
        self.database = database
        self.etherscan = etherscan
        self.inquirers: dict[SupportedBlockchain, 'EvmNodeInquirer'] = {}
        self._lock = asyncio.Lock()

    async def get_inquirer(self, blockchain: SupportedBlockchain) -> 'EvmNodeInquirer':
        """Get or create a node inquirer for the specified blockchain"""
        async with self._lock:
            if blockchain not in self.inquirers:
                # Create the appropriate inquirer based on blockchain
                if blockchain == SupportedBlockchain.OPTIMISM:
                    self.inquirers[blockchain] = OptimismInquirer(
                        database=self.database,
                        etherscan=self.etherscan,
                    )
                else:
                    raise NotImplementedError(f'Inquirer for {blockchain} not implemented yet')
                
                # Connect to nodes if we have tracked accounts
                await self.inquirers[blockchain].maybe_connect_to_nodes(when_tracked_accounts=True)
            
            return self.inquirers[blockchain]

    async def get_native_token_balance(
            self,
            blockchain: SupportedBlockchain,
            address: ChecksumEvmAddress,
    ) -> str:
        """Get the native token balance for an address on a blockchain"""
        inquirer = await self.get_inquirer(blockchain)
        balances = await inquirer.get_multi_balance([address])
        return str(balances.get(address, 0))

    async def get_erc20_token_info(
            self,
            blockchain: SupportedBlockchain,
            token_address: ChecksumEvmAddress,
    ) -> dict[str, Any]:
        """Get ERC20 token information"""
        inquirer = await self.get_inquirer(blockchain)
        return await inquirer.get_erc20_contract_info(token_address)

    async def get_transaction_receipt(
            self,
            blockchain: SupportedBlockchain,
            tx_hash: str,
    ) -> dict[str, Any] | None:
        """Get transaction receipt"""
        inquirer = await self.get_inquirer(blockchain)
        from rotkehlchen.types import EVMTxHash
        
        try:
            # Convert hex string to EVMTxHash
            if tx_hash.startswith('0x'):
                tx_hash = tx_hash[2:]
            tx_hash_bytes = bytes.fromhex(tx_hash)
            return await inquirer.get_transaction_receipt(EVMTxHash(tx_hash_bytes))
        except Exception as e:
            logger.error(f'Failed to get transaction receipt: {e}')
            return None

    async def call_contract_method(
            self,
            blockchain: SupportedBlockchain,
            contract_address: ChecksumEvmAddress,
            abi: list[dict[str, Any]],
            method_name: str,
            arguments: list[Any] | None = None,
    ) -> Any:
        """Call a contract method"""
        inquirer = await self.get_inquirer(blockchain)
        return await inquirer.call_contract(
            contract_address=contract_address,
            abi=abi,
            method_name=method_name,
            arguments=arguments,
        )

    async def get_logs(
            self,
            blockchain: SupportedBlockchain,
            contract_address: ChecksumEvmAddress,
            abi: list[dict[str, Any]],
            event_name: str,
            from_block: int,
            to_block: int | str = 'latest',
            argument_filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get contract event logs"""
        inquirer = await self.get_inquirer(blockchain)
        return await inquirer.get_logs(
            contract_address=contract_address,
            abi=abi,
            event_name=event_name,
            argument_filters=argument_filters or {},
            from_block=from_block,
            to_block=to_block,
        )

    async def add_rpc_node(
            self,
            blockchain: SupportedBlockchain,
            name: str,
            endpoint: str,
            weight: float = 1.0,
            active: bool = True,
    ) -> dict[str, Any]:
        """Add a new RPC node for a blockchain"""
        # Store in database
        node_info = await self.database.add_rpc_node(
            blockchain=blockchain,
            name=name,
            endpoint=endpoint,
            weight=weight,
            active=active,
        )
        
        # If we have an active inquirer, try to connect to the new node
        if blockchain in self.inquirers and active:
            from rotki2.chain.evm.types import NodeName, WeightedNode
            
            node = NodeName(
                name=name,
                endpoint=endpoint,
                owned=True,
                blockchain=blockchain,
            )
            weighted_node = WeightedNode(
                node_info=node,
                active=active,
                weight=weight,
                identifier=node_info['identifier'],
            )
            
            success, message = await self.inquirers[blockchain].attempt_connect(node)
            node_info['connected'] = success
            node_info['connection_message'] = message
        
        return node_info

    async def test_rpc_endpoint(
            self,
            blockchain: SupportedBlockchain,
            endpoint: str,
    ) -> dict[str, Any]:
        """Test if an RPC endpoint is reachable and on the correct network"""
        from rotki2.chain.evm.types import NodeName
        
        inquirer = await self.get_inquirer(blockchain)
        node = NodeName(
            name='test_node',
            endpoint=endpoint,
            owned=True,
            blockchain=blockchain,
        )
        
        success, message = await inquirer.attempt_connect(node, connectivity_check=True)
        
        result = {
            'success': success,
            'message': message,
        }
        
        if success:
            # Get additional info if connection successful
            web3node = inquirer.web3_mapping.get(node)
            if web3node:
                result['is_archive'] = web3node.is_archive
                result['is_pruned'] = web3node.is_pruned
                try:
                    result['latest_block'] = await inquirer.get_latest_block_number()
                except Exception:
                    pass
                
                # Clean up test connection
                inquirer.web3_mapping.pop(node, None)
        
        return result