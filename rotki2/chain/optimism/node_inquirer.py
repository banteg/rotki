"""Async Optimism node inquirer"""
import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EVMTxHash, SupportedBlockchain

from rotki2.chain.evm.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotki2.chain.evm.l2_with_l1_fees.node_inquirer import (
    DSProxyL2WithL1FeesInquirerWithCacheData,
)
from rotki2.chain.evm.types import string_to_evm_address

from .constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    PRUNED_NODE_CHECK_TX_HASH,
)

if TYPE_CHECKING:
    from rotkehlchen.externalapis.etherscan import Etherscan

    from rotki2.api.v2.services.database import DatabaseService

logger = logging.getLogger(__name__)
log = logger


class OptimismInquirer(DSProxyL2WithL1FeesInquirerWithCacheData):
    """Async Optimism node inquirer"""

    def __init__(
            self,
            database: 'DatabaseService',
            etherscan: 'Etherscan',
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        contracts = EvmContracts[Literal[ChainID.OPTIMISM]](chain_id=ChainID.OPTIMISM)
        super().__init__(
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.OPTIMISM,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0x2DC0E2aa608532Da689e89e237dF582B783E552C')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            dsproxy_registry=contracts.contract(string_to_evm_address('0x283Cc5C26e53D66ed2Ea252D986F094B37E6e895')),
            native_token=A_ETH.resolve_to_crypto_asset(),
            blockscout=Blockscout(
                blockchain=SupportedBlockchain.OPTIMISM,
                database=database,
                msg_aggregator=database.msg_aggregator,
            ),
        )

    # -- Implementation of EvmNodeInquirer base methods --

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )