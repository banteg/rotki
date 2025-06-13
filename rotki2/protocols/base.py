"""Base protocol handler interface."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rotki2.chain.evm.node_inquirer import EvmNodeInquirer


class ProtocolHandler(ABC):
    """Base class for all protocol handlers."""
    
    def __init__(self, inquirer: 'EvmNodeInquirer') -> None:
        self.inquirer = inquirer
        self.chain_id = inquirer.chain_id
    
    @abstractmethod
    def get_decoding_rules(self) -> dict[str, Any]:
        """Return decoding rules for this protocol on the current chain."""
        ...
    
    @abstractmethod
    def get_protocol_name(self) -> str:
        """Return the protocol name."""
        ...
    
    def get_balances(self, address: str) -> dict[str, Any]:
        """Get protocol-specific balances for an address."""
        return {}