"""Generic Aave V3 handler for any supported chain."""
from typing import TYPE_CHECKING, Any

from rotkehlchen.types import ChecksumEvmAddress
from rotki2.protocols.base import ProtocolHandler

from .constants import (
    AAVE_V3_INCENTIVES_CONTROLLERS,
    AAVE_V3_NATIVE_GATEWAYS,
    AAVE_V3_POOLS,
    BORROW_SIGNATURE,
    BURN_SIGNATURE,
    DEPOSIT_SIGNATURE,
    REPAY_SIGNATURE,
    REWARDS_CLAIMED_SIGNATURE,
)

if TYPE_CHECKING:
    from rotki2.chain.evm.node_inquirer import EvmNodeInquirer


class AaveV3(ProtocolHandler):
    """Generic Aave V3 handler for any supported chain."""
    
    def __init__(self, inquirer: 'EvmNodeInquirer') -> None:
        super().__init__(inquirer)
        self.pools = AAVE_V3_POOLS.get(self.chain_id, [])
        self.native_gateway = AAVE_V3_NATIVE_GATEWAYS.get(self.chain_id)
        self.incentives_controller = AAVE_V3_INCENTIVES_CONTROLLERS.get(self.chain_id)
    
    def get_protocol_name(self) -> str:
        """Return the protocol name."""
        return 'Aave V3'
    
    def get_decoding_rules(self) -> dict[str, Any]:
        """Return decoding rules for Aave V3 on the current chain."""
        if not self.pools:
            return {}
        
        rules = {
            'events': {
                # Deposit events from pools
                DEPOSIT_SIGNATURE.hex(): {
                    'name': 'Deposit',
                    'handler': self._decode_deposit,
                    'addresses': self.pools,
                },
                # Borrow events from pools
                BORROW_SIGNATURE.hex(): {
                    'name': 'Borrow',
                    'handler': self._decode_borrow,
                    'addresses': self.pools,
                },
                # Repay events from pools
                REPAY_SIGNATURE.hex(): {
                    'name': 'Repay',
                    'handler': self._decode_repay,
                    'addresses': self.pools,
                },
                # Withdrawal/burn events from pools
                BURN_SIGNATURE.hex(): {
                    'name': 'Burn',
                    'handler': self._decode_burn,
                    'addresses': self.pools,
                },
            },
            'transactions': {},
        }
        
        # Add incentives controller events if available
        if self.incentives_controller:
            rules['events'][REWARDS_CLAIMED_SIGNATURE.hex()] = {
                'name': 'RewardsClaimed',
                'handler': self._decode_rewards_claimed,
                'addresses': [self.incentives_controller],
            }
        
        # Add native gateway transactions if available
        if self.native_gateway:
            rules['transactions']['depositETH'] = {
                'addresses': [self.native_gateway],
                'handler': self._decode_deposit_eth,
            }
            rules['transactions']['withdrawETH'] = {
                'addresses': [self.native_gateway],
                'handler': self._decode_withdraw_eth,
            }
        
        return rules
    
    async def _decode_deposit(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a deposit event."""
        return {
            'action': 'deposit',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'event': event_data,
        }
    
    async def _decode_borrow(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a borrow event."""
        return {
            'action': 'borrow',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'event': event_data,
        }
    
    async def _decode_repay(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a repay event."""
        return {
            'action': 'repay',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'event': event_data,
        }
    
    async def _decode_burn(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a burn/withdrawal event."""
        return {
            'action': 'withdraw',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'event': event_data,
        }
    
    async def _decode_rewards_claimed(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a rewards claimed event."""
        return {
            'action': 'claim_rewards',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'event': event_data,
        }
    
    async def _decode_deposit_eth(self, tx_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a native ETH deposit transaction."""
        return {
            'action': 'deposit_native',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'transaction': tx_data,
        }
    
    async def _decode_withdraw_eth(self, tx_data: dict[str, Any]) -> dict[str, Any]:
        """Decode a native ETH withdrawal transaction."""
        return {
            'action': 'withdraw_native',
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'transaction': tx_data,
        }
    
    async def get_balances(self, address: ChecksumEvmAddress) -> dict[str, Any]:
        """Get Aave V3 positions for an address."""
        if not self.pools:
            return {}
        
        # This would query the Aave data provider for user positions
        # For now, returning a placeholder structure
        return {
            'protocol': self.get_protocol_name(),
            'chain_id': self.chain_id,
            'positions': {
                'deposits': [],
                'borrows': [],
            },
        }