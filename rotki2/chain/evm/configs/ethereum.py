"""Ethereum chain configuration."""
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain, Timestamp
from rotki2.chain.ethereum.node_inquirer import EthereumInquirer
from rotki2.protocols import aave, uniswap

from .base import ChainConfig
from .registry import register_chain_config

ETHEREUM_CONFIG = ChainConfig(
    name='Ethereum',
    chain_id=ChainID.ETHEREUM,
    blockchain=SupportedBlockchain.ETHEREUM,
    inquirer_class=EthereumInquirer,
    native_token=A_ETH,
    supported_protocols=[
        aave.AaveV3,
        uniswap.UniswapV3,
        # Add more protocols as they are migrated
    ],
    genesis_ts=Timestamp(1438269973),
    pruned_tx_hash='0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060',
    archive_check_addr=ChecksumEvmAddress('0x50532e4Be195D1dE0c2E6DfA46D9ec0a4Fee6861'),
    archive_check_block=87042,
    archive_check_expected_balance=5_106_330_700_000_000_000,  # 5.1063307 ETH in wei
    etherscan_node='etherscan.io',
    etherscan_api_key_name='etherscan',
    supports_eip1559=True,
    supports_trace_api=True,
)

# Register the configuration
register_chain_config(ETHEREUM_CONFIG)