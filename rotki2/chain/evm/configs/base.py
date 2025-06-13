"""Base chain configuration dataclass."""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Type

from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain, Timestamp

if TYPE_CHECKING:
    from rotki2.chain.evm.node_inquirer import EvmNodeInquirer
    from rotki2.protocols.base import ProtocolHandler


@dataclass(frozen=True)
class ChainConfig:
    """A configuration object holding all chain-specific details."""
    
    name: str
    chain_id: ChainID
    blockchain: SupportedBlockchain
    inquirer_class: Type['EvmNodeInquirer']
    native_token: Asset
    supported_protocols: list[Type['ProtocolHandler']] = field(default_factory=list)
    
    # Chain-specific constants
    genesis_ts: Timestamp = Timestamp(0)
    pruned_tx_hash: str = ''
    archive_check_addr: ChecksumEvmAddress = ChecksumEvmAddress('0x0000000000000000000000000000000000000000')
    archive_check_block: int = 0
    archive_check_expected_balance: int = 0
    
    # Etherscan or block explorer configuration
    etherscan_node: str | None = None
    etherscan_api_key_name: str | None = None
    
    # Optional features
    supports_eip1559: bool = True
    supports_trace_api: bool = False
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.pruned_tx_hash:
            raise ValueError(f'Chain {self.name} must have a pruned_tx_hash')
        if self.archive_check_block == 0:
            raise ValueError(f'Chain {self.name} must have archive_check_block set')