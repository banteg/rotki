"""Test async EVM node inquirer implementation"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from web3 import AsyncWeb3

from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain

from rotki2.chain.evm.node_inquirer import EvmNodeInquirer
from rotki2.chain.evm.types import NodeName, Web3Node, WeightedNode
from rotki2.chain.optimism.node_inquirer import OptimismInquirer


class MockEvmInquirer(EvmNodeInquirer):
    """Mock implementation for testing base functionality"""
    
    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ChecksumEvmAddress('0x1234567890123456789012345678901234567890'),
            100,
            FVal('1.0'),
        )
    
    def _get_pruned_check_tx_hash(self):
        from rotkehlchen.types import EVMTxHash
        return EVMTxHash(b'0' * 32)


@pytest.fixture
def mock_database():
    """Create a mock database service"""
    db = AsyncMock()
    db.get_blockchain_accounts = AsyncMock(return_value={})
    db.get_rpc_nodes = AsyncMock(return_value=[])
    db.msg_aggregator = MagicMock()
    return db


@pytest.fixture
def mock_etherscan():
    """Create a mock etherscan service"""
    etherscan = MagicMock()
    etherscan.get_latest_block_number = MagicMock(return_value=1000000)
    return etherscan


@pytest.fixture
def mock_contracts():
    """Create mock contracts"""
    contracts = MagicMock()
    contracts.erc20_abi = []
    contracts.erc721_abi = []
    contracts.univ1lp_abi = []
    return contracts


@pytest.fixture
def mock_contract():
    """Create a mock contract"""
    contract = MagicMock()
    contract.address = ChecksumEvmAddress('0x0000000000000000000000000000000000000001')
    contract.call = AsyncMock()
    return contract


@pytest.mark.asyncio
async def test_evm_inquirer_initialization(mock_database, mock_etherscan, mock_contracts, mock_contract):
    """Test that EVM inquirer initializes correctly"""
    from rotkehlchen.constants.assets import A_ETH
    
    inquirer = MockEvmInquirer(
        database=mock_database,
        etherscan=mock_etherscan,
        blockchain=SupportedBlockchain.OPTIMISM,
        contracts=mock_contracts,
        contract_scan=mock_contract,
        contract_multicall=mock_contract,
        native_token=A_ETH.resolve_to_crypto_asset(),
    )
    
    assert inquirer.blockchain == SupportedBlockchain.OPTIMISM
    assert inquirer.chain_id == ChainID.OPTIMISM
    assert inquirer.chain_name == 'Optimism'
    assert not inquirer.connected_to_any_web3()
    assert len(inquirer.web3_mapping) == 0


@pytest.mark.asyncio
async def test_web3_connection():
    """Test connecting to a Web3 node"""
    mock_web3 = AsyncMock(spec=AsyncWeb3)
    mock_web3.is_connected = AsyncMock(return_value=True)
    mock_web3.net.version = '10'  # Optimism chain ID
    mock_web3.eth.block_number = 1000000
    
    with patch('rotki2.chain.evm.node_inquirer.AsyncWeb3', return_value=mock_web3):
        with patch('rotki2.chain.evm.node_inquirer.AsyncHTTPProvider'):
            from rotkehlchen.constants.assets import A_ETH
            
            mock_database = AsyncMock()
            mock_database.get_blockchain_accounts = AsyncMock(return_value={})
            mock_database.get_rpc_nodes = AsyncMock(return_value=[])
            
            inquirer = MockEvmInquirer(
                database=mock_database,
                etherscan=MagicMock(),
                blockchain=SupportedBlockchain.OPTIMISM,
                contracts=MagicMock(),
                contract_scan=MagicMock(),
                contract_multicall=MagicMock(),
                native_token=A_ETH.resolve_to_crypto_asset(),
            )
            
            node = NodeName(
                name='test_node',
                endpoint='http://localhost:8545',
                owned=True,
                blockchain=SupportedBlockchain.OPTIMISM,
            )
            
            success, message = await inquirer.attempt_connect(node)
            
            assert success is True
            assert 'Connected' in message or 'Already connected' in message
            assert inquirer.connected_to_any_web3()


@pytest.mark.asyncio
async def test_get_multi_balance(mock_database, mock_etherscan, mock_contracts, mock_contract):
    """Test getting multiple account balances"""
    from rotkehlchen.constants.assets import A_ETH
    
    # Mock contract call to return balances
    mock_contract.call = AsyncMock(return_value=[1000000000000000000, 2000000000000000000])  # 1 ETH, 2 ETH
    
    inquirer = MockEvmInquirer(
        database=mock_database,
        etherscan=mock_etherscan,
        blockchain=SupportedBlockchain.OPTIMISM,
        contracts=mock_contracts,
        contract_scan=mock_contract,
        contract_multicall=mock_contract,
        native_token=A_ETH.resolve_to_crypto_asset(),
    )
    
    addresses = [
        ChecksumEvmAddress('0x1234567890123456789012345678901234567890'),
        ChecksumEvmAddress('0x0987654321098765432109876543210987654321'),
    ]
    
    balances = await inquirer.get_multi_balance(addresses)
    
    assert len(balances) == 2
    assert balances[addresses[0]] == FVal('1')
    assert balances[addresses[1]] == FVal('2')


@pytest.mark.asyncio
async def test_optimism_inquirer_initialization(mock_database, mock_etherscan):
    """Test Optimism-specific inquirer initialization"""
    inquirer = OptimismInquirer(
        database=mock_database,
        etherscan=mock_etherscan,
    )
    
    assert inquirer.blockchain == SupportedBlockchain.OPTIMISM
    assert inquirer.chain_id == ChainID.OPTIMISM
    
    # Test archive check data
    address, block, balance = inquirer._get_archive_check_data()
    assert isinstance(address, str)
    assert isinstance(block, int)
    assert isinstance(balance, FVal)
    
    # Test pruned check tx hash
    tx_hash = inquirer._get_pruned_check_tx_hash()
    assert len(tx_hash) == 32  # 32 bytes for transaction hash


@pytest.mark.asyncio
async def test_call_order_generation(mock_database, mock_etherscan, mock_contracts, mock_contract):
    """Test default call order generation"""
    from rotkehlchen.constants.assets import A_ETH
    
    # Mock some RPC nodes
    mock_nodes = [
        WeightedNode(
            node_info=NodeName('node1', 'http://node1.com', False, SupportedBlockchain.OPTIMISM),
            active=True,
            weight=FVal('0.5'),
        ),
        WeightedNode(
            node_info=NodeName('node2', 'http://node2.com', False, SupportedBlockchain.OPTIMISM),
            active=True,
            weight=FVal('0.3'),
        ),
        WeightedNode(
            node_info=NodeName('owned_node', 'http://owned.com', True, SupportedBlockchain.OPTIMISM),
            active=True,
            weight=FVal('1.0'),
        ),
    ]
    
    mock_database.get_rpc_nodes = MagicMock(return_value=mock_nodes)
    
    inquirer = MockEvmInquirer(
        database=mock_database,
        etherscan=mock_etherscan,
        blockchain=SupportedBlockchain.OPTIMISM,
        contracts=mock_contracts,
        contract_scan=mock_contract,
        contract_multicall=mock_contract,
        native_token=A_ETH.resolve_to_crypto_asset(),
    )
    
    call_order = inquirer.default_call_order()
    
    # Owned nodes should be first
    assert call_order[0].node_info.owned is True
    # Etherscan should be last (unless skip_etherscan=True)
    assert 'etherscan' in call_order[-1].node_info.name


@pytest.mark.asyncio
async def test_concurrent_node_connections(mock_database, mock_etherscan, mock_contracts, mock_contract):
    """Test connecting to multiple nodes concurrently"""
    from rotkehlchen.constants.assets import A_ETH
    
    mock_web3 = AsyncMock(spec=AsyncWeb3)
    mock_web3.is_connected = AsyncMock(return_value=True)
    mock_web3.net.version = '10'
    mock_web3.eth.block_number = 1000000
    
    with patch('rotki2.chain.evm.node_inquirer.AsyncWeb3', return_value=mock_web3):
        with patch('rotki2.chain.evm.node_inquirer.AsyncHTTPProvider'):
            inquirer = MockEvmInquirer(
                database=mock_database,
                etherscan=mock_etherscan,
                blockchain=SupportedBlockchain.OPTIMISM,
                contracts=mock_contracts,
                contract_scan=mock_contract,
                contract_multicall=mock_contract,
                native_token=A_ETH.resolve_to_crypto_asset(),
            )
            
            nodes = [
                WeightedNode(
                    node_info=NodeName(f'node{i}', f'http://node{i}.com', False, SupportedBlockchain.OPTIMISM),
                    active=True,
                    weight=FVal('1.0'),
                )
                for i in range(3)
            ]
            
            await inquirer.connect_to_multiple_nodes(nodes)
            
            # All nodes should be connected
            assert len(inquirer.web3_mapping) == 3


if __name__ == '__main__':
    # Run tests
    asyncio.run(test_evm_inquirer_initialization(
        mock_database=AsyncMock(),
        mock_etherscan=MagicMock(),
        mock_contracts=MagicMock(),
        mock_contract=MagicMock(),
    ))