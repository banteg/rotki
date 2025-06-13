"""Arbitrum One chain configuration."""
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain, Timestamp
from rotki2.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
from rotki2.protocols import aave, uniswap

from .base import ChainConfig
from .registry import register_chain_config

ARBITRUM_CONFIG = ChainConfig(
    name='Arbitrum One',
    chain_id=ChainID.ARBITRUM_ONE,
    blockchain=SupportedBlockchain.ARBITRUM_ONE,
    inquirer_class=ArbitrumOneInquirer,
    native_token=A_ETH,
    supported_protocols=[
        aave.AaveV3,
        uniswap.UniswapV3,
        # Add more protocols as they are migrated
    ],
    genesis_ts=Timestamp(1622240000),
    pruned_tx_hash='0x7eef161b36d4f4708fd82d6c050c0b970a1d321f6dcf2c4591dc039f74cc1ab5',
    archive_check_addr=ChecksumEvmAddress('0x2EE4bD21803cdb62B1457949450d0753ca84fada'),
    archive_check_block=42,
    archive_check_expected_balance=500_000_000_000_000_000,  # 0.5 ETH in wei
    etherscan_node='arbiscan.io',
    etherscan_api_key_name='arbiscan',
    supports_eip1559=True,
    supports_trace_api=False,
)

# Register the configuration
register_chain_config(ARBITRUM_CONFIG)