"""Optimism chain configuration."""
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain, Timestamp
from rotki2.chain.optimism.node_inquirer import OptimismInquirer
from rotki2.protocols import aave, uniswap

from .base import ChainConfig
from .registry import register_chain_config

OPTIMISM_CONFIG = ChainConfig(
    name='Optimism',
    chain_id=ChainID.OPTIMISM,
    blockchain=SupportedBlockchain.OPTIMISM,
    inquirer_class=OptimismInquirer,
    native_token=A_ETH,
    supported_protocols=[
        aave.AaveV3,
        uniswap.UniswapV3,
        # Add more protocols as they are migrated
    ],
    genesis_ts=Timestamp(1636666246),
    pruned_tx_hash='0x5e77a04531c7c107af1882d76cbff9486d0a9aa53701c30888509d4f5f2b003a',
    archive_check_addr=ChecksumEvmAddress('0x76a05Df20bFEF5EcE3eB16afF9cb10134199A921'),
    archive_check_block=74000,
    archive_check_expected_balance=50_000_000_000_000_000,  # 0.05 ETH in wei
    etherscan_node='optimistic.etherscan.io',
    etherscan_api_key_name='optimism_etherscan',
    supports_eip1559=True,
    supports_trace_api=False,
)

# Register the configuration
register_chain_config(OPTIMISM_CONFIG)