"""Generic Uniswap V3 handler for any supported chain."""
from typing import TYPE_CHECKING, Any

from rotkehlchen.types import ChecksumEvmAddress
from rotki2.protocols.base import ProtocolHandler

from .constants import (
    COLLECT_LIQUIDITY_SIGNATURE,
    INCREASE_LIQUIDITY_SIGNATURE,
    SWAP_SIGNATURE,
    UNISWAP_UNIVERSAL_ROUTERS,
    UNISWAP_V3_NFT_MANAGERS,
    UNISWAP_V3_ROUTERS,
)

if TYPE_CHECKING:
    from rotki2.chain.evm.node_inquirer import EvmNodeInquirer


class UniswapV3(ProtocolHandler):
    """Generic Uniswap V3 handler for any supported chain."""
    
    def __init__(self, inquirer: 'EvmNodeInquirer') -> None:
        super().__init__(inquirer)
        self.router_address = UNISWAP_V3_ROUTERS.get(self.chain_id)
        self.nft_manager_address = UNISWAP_V3_NFT_MANAGERS.get(self.chain_id)
        self.universal_router_address = UNISWAP_UNIVERSAL_ROUTERS.get(self.chain_id)
    
    def get_protocol_name(self) -> str:
        """Return the protocol name."""
        return 'Uniswap V3'
    
    def get_decoding_rules(self) -> dict[str, Any]:
        """Return decoding rules for Uniswap V3 on the current chain."""
        if not self.router_address:
            return {}
        
        rules = {
            'events': {
                # Swap events from pools
                SWAP_SIGNATURE.hex(): {
                    'name': 'Swap',
                    'handler': self._decode_swap_event,
                },
                # LP position events from NFT manager
                INCREASE_LIQUIDITY_SIGNATURE.hex(): {
                    'name': 'IncreaseLiquidity',
                    'handler': self._decode_increase_liquidity,
                    'addresses': [self.nft_manager_address] if self.nft_manager_address else [],
                },
                COLLECT_LIQUIDITY_SIGNATURE.hex(): {
                    'name': 'Collect',
                    'handler': self._decode_collect,
                    'addresses': [self.nft_manager_address] if self.nft_manager_address else [],
                },
            },
            'transactions': {
                # Router transactions
                'multicall': {
                    'addresses': [self.router_address],
                    'handler': self._decode_multicall,
                },
                # Universal router transactions
                'execute': {
                    'addresses': [self.universal_router_address] if self.universal_router_address else [],
                    'handler': self._decode_universal_router_execute,
                },
            },
        }
        
        return rules
    
    async def _decode_swap_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a swap event."""
        # Implementation would decode the swap event data
        # This is a placeholder for the actual implementation
        return {
            'action': 'swap',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'event': event_data,
        }
    
    async def _decode_increase_liquidity(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Decode an increase liquidity event."""
        return {
            'action': 'add_liquidity',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'event': event_data,
        }
    
    async def _decode_collect(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a collect event."""
        return {
            'action': 'collect_fees',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'event': event_data,
        }
    
    async def _decode_multicall(self, tx_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a multicall transaction."""
        return {
            'action': 'multicall',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'transaction': tx_data,
        }
    
    async def _decode_universal_router_execute(self, tx_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a universal router execute transaction."""
        return {
            'action': 'universal_router_execute',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'transaction': tx_data,
        }
    
    async def get_balances(self, address: ChecksumEvmAddress) -> dict[str, Any]:
        """Get Uniswap V3 LP positions for an address."""
        if not self.nft_manager_address:
            return {}
        
        # This would query the NFT manager for LP positions
        # and calculate their values
        return {
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'positions': [],
        }