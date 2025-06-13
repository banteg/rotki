"""Optimism-specific constants"""
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash

from rotki2.chain.evm.types import string_to_evm_address

# Constants for checking if a node is pruned
PRUNED_NODE_CHECK_TX_HASH = EVMTxHash(bytes.fromhex('19e5f5dc773f8a0850e96d193bea69bd6a28dd018d9fb8f3971f8d582ecbf8ea'))  # noqa: E501

# Constants for checking if a node is an archive node
ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0x82311f5aA3d3f7d37D6082Cc5e719120dd8ac397')
ARCHIVE_NODE_CHECK_BLOCK = 15565484
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('0.108854406283168012')