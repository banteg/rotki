"""Liquity protocol service for async operations"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Timestamp

from .base import AsyncDeFiProtocolService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from rotki2.api.v2.repositories.history_events import HistoryEventsRepository
    from rotki2.utils.async_http_client import AsyncHTTPClient


class AsyncLiquityService(AsyncDeFiProtocolService):
    """Async service for Liquity protocol operations
    
    Handles Liquity troves, stability pool, and LQTY staking
    """
    
    def __init__(
        self,
        session: 'AsyncSession',
        http_client: 'AsyncHTTPClient | None' = None,
        history_repo: 'HistoryEventsRepository | None' = None,
    ):
        super().__init__(session, http_client, history_repo)
        
    @property
    def protocol_name(self) -> str:
        """Return the protocol name"""
        return 'liquity'
        
    async def get_balances(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[Asset, Balance]]:
        """Get current Liquity balances (troves, stability pool, staking)"""
        balances = {}
        
        for address in addresses:
            address_balances = {}
            
            # Get trove positions (collateral and debt)
            trove = await self._get_trove_position(address)
            if trove:
                # ETH collateral
                collateral = trove.get('collateral', ZERO)
                if collateral > ZERO:
                    address_balances[Asset('ETH')] = Balance(
                        amount=collateral,
                        usd_value=trove.get('collateral_usd', ZERO),
                    )
                    
                # LUSD debt
                debt = trove.get('debt', ZERO)
                if debt > ZERO:
                    address_balances[Asset('LUSD_DEBT')] = Balance(
                        amount=-debt,  # Negative for debt
                        usd_value=-debt,  # LUSD is pegged to $1
                    )
            
            # Get stability pool deposits
            stability = await self._get_stability_pool_position(address)
            if stability:
                deposit = stability.get('lusd_deposit', ZERO)
                if deposit > ZERO:
                    address_balances[Asset('LUSD')] = Balance(
                        amount=deposit,
                        usd_value=deposit,  # LUSD is pegged to $1
                    )
                    
            # Get LQTY staking
            staking = await self._get_staking_position(address)
            if staking:
                staked_lqty = staking.get('staked_lqty', ZERO)
                if staked_lqty > ZERO:
                    address_balances[Asset('LQTY')] = Balance(
                        amount=staked_lqty,
                        usd_value=staking.get('staked_usd', ZERO),
                    )
                    
            if address_balances:
                balances[address] = address_balances
                
        return balances
        
    async def get_positions(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[dict[str, Any]]]:
        """Get all Liquity positions for given addresses"""
        positions = {}
        
        for address in addresses:
            address_positions = []
            
            # Get trove position
            trove = await self._get_trove_position(address)
            if trove:
                position = {
                    'type': 'trove',
                    'collateral_eth': str(trove.get('collateral', '0')),
                    'debt_lusd': str(trove.get('debt', '0')),
                    'collateral_ratio': str(trove.get('collateral_ratio', '0')),
                    'liquidation_price': str(trove.get('liquidation_price', '0')),
                    'status': trove.get('status', 'active'),
                    'icr': str(trove.get('icr', '0')),  # Individual Collateral Ratio
                    'stake': str(trove.get('stake', '0')),
                }
                address_positions.append(position)
                
            # Get stability pool position
            stability = await self._get_stability_pool_position(address)
            if stability:
                position = {
                    'type': 'stability_pool',
                    'lusd_deposit': str(stability.get('lusd_deposit', '0')),
                    'eth_gain': str(stability.get('eth_gain', '0')),
                    'lqty_gain': str(stability.get('lqty_gain', '0')),
                    'snapshot_lusd': str(stability.get('snapshot_lusd', '0')),
                    'snapshot_eth': str(stability.get('snapshot_eth', '0')),
                }
                address_positions.append(position)
                
            # Get LQTY staking position
            staking = await self._get_staking_position(address)
            if staking:
                position = {
                    'type': 'lqty_staking',
                    'staked_lqty': str(staking.get('staked_lqty', '0')),
                    'eth_reward': str(staking.get('eth_reward', '0')),
                    'lusd_reward': str(staking.get('lusd_reward', '0')),
                    'staked_usd': str(staking.get('staked_usd', '0')),
                }
                address_positions.append(position)
                
            if address_positions:
                positions[address] = address_positions
                
        return positions
        
    async def _get_trove_position(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, Any] | None:
        """Get trove position for an address
        
        In production, this would query Liquity's TroveManager contract
        """
        # Mock data for demonstration
        # Return None for some addresses to simulate no position
        if hash(address) % 3 == 0:
            return None
            
        return {
            'collateral': FVal('10'),  # 10 ETH
            'collateral_usd': FVal('16000'),  # At $1600/ETH
            'debt': FVal('8000'),  # 8000 LUSD
            'collateral_ratio': FVal('2.0'),  # 200%
            'liquidation_price': FVal('727.27'),  # ETH price at 110% ratio
            'status': 'active',
            'icr': FVal('2.0'),  # Individual Collateral Ratio
            'stake': FVal('8000'),  # Trove stake for liquidation rewards
        }
        
    async def _get_stability_pool_position(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, Any] | None:
        """Get stability pool position for an address
        
        In production, this would query StabilityPool contract
        """
        # Mock data for demonstration
        if hash(address) % 2 == 0:
            return None
            
        return {
            'lusd_deposit': FVal('5000'),
            'eth_gain': FVal('0.25'),  # From liquidations
            'lqty_gain': FVal('50'),  # LQTY rewards
            'snapshot_lusd': FVal('4950'),  # For calculating gains
            'snapshot_eth': FVal('0.20'),
        }
        
    async def _get_staking_position(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, Any] | None:
        """Get LQTY staking position for an address
        
        In production, this would query LQTYStaking contract
        """
        # Mock data for demonstration
        if hash(address) % 4 == 0:
            return None
            
        return {
            'staked_lqty': FVal('1000'),
            'eth_reward': FVal('0.15'),  # From borrowing fees
            'lusd_reward': FVal('100'),  # From redemption fees
            'staked_usd': FVal('5000'),  # At $5/LQTY
        }
        
    async def get_protocol_stats(self) -> dict[str, Any]:
        """Get Liquity protocol statistics"""
        # In production, would query from Liquity contracts
        return {
            'protocol': self.protocol_name,
            'tvl': '650000000',  # $650M
            'total_collateral_eth': '406250',  # 406,250 ETH
            'total_debt_lusd': '325000000',  # 325M LUSD
            'total_collateral_ratio': '2.0',  # 200% system-wide
            'recovery_mode': False,  # TCR > 150%
            'base_rate': '0.005',  # 0.5%
            'borrowing_fee_floor': '0.005',  # 0.5%
            'redemption_fee_floor': '0.005',  # 0.5%
            'trove_count': 2150,
            'stability_pool': {
                'total_lusd': '180000000',  # 180M LUSD
                'total_providers': 3500,
            },
            'staking': {
                'total_lqty_staked': '15000000',  # 15M LQTY
                'total_stakers': 1200,
            },
        }
        
    async def get_liquidation_history(
        self,
        address: ChecksumEvmAddress,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> list[dict[str, Any]]:
        """Get liquidation history for an address"""
        if not self.history_repo:
            return []
            
        # Query liquidation events
        events = await self.history_repo.get_defi_events_by_protocol(
            protocol=self.protocol_name,
            account=address,
            start_timestamp=from_timestamp,
            end_timestamp=to_timestamp,
        )
        
        liquidations = []
        for event in events:
            if hasattr(event, 'event_subtype') and event.event_subtype and 'liquidate' in event.event_subtype.value.lower():
                liquidations.append({
                    'timestamp': event.timestamp,
                    'collateral_eth': str(event.balance.amount),
                    'debt_lusd': str(event.extra_data.get('debt', '0')) if hasattr(event, 'extra_data') else '0',
                    'liquidator': event.location_label if hasattr(event, 'location_label') else 'Unknown',
                    'tx_hash': event.tx_hash if hasattr(event, 'tx_hash') else '',
                })
                
        return liquidations
        
    async def get_trove_operations(
        self,
        address: ChecksumEvmAddress,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> list[dict[str, Any]]:
        """Get trove operation history (open, adjust, close)"""
        if not self.history_repo:
            return []
            
        # Query trove events
        events = await self.history_repo.get_defi_events_by_protocol(
            protocol=self.protocol_name,
            account=address,
            start_timestamp=from_timestamp,
            end_timestamp=to_timestamp,
        )
        
        operations = []
        for event in events:
            if hasattr(event, 'event_subtype') and event.event_subtype:
                subtype = event.event_subtype.value.lower()
                if any(op in subtype for op in ['open', 'adjust', 'close']):
                    operations.append({
                        'timestamp': event.timestamp,
                        'operation': subtype,
                        'collateral_change': str(event.balance.amount),
                        'debt_change': str(event.extra_data.get('debt_change', '0')) if hasattr(event, 'extra_data') else '0',
                        'tx_hash': event.tx_hash if hasattr(event, 'tx_hash') else '',
                    })
                    
        return operations
        
    async def calculate_redemption_hint(
        self,
        lusd_amount: FVal,
    ) -> dict[str, Any]:
        """Calculate redemption hint for optimal gas usage
        
        In production, this helps users redeem LUSD efficiently
        """
        # Mock calculation
        partial_redemption_hint = '0x1234567890abcdef1234567890abcdef12345678'
        truncated_lusd_amount = lusd_amount * FVal('0.999')  # Account for fees
        
        return {
            'partial_redemption_hint': partial_redemption_hint,
            'truncated_lusd_amount': str(truncated_lusd_amount),
            'estimated_eth_received': str(truncated_lusd_amount / FVal('1600')),  # At current price
            'redemption_fee': str(lusd_amount * FVal('0.005')),  # 0.5% fee
        }
        
    async def get_recovery_mode_status(self) -> dict[str, Any]:
        """Check if system is in recovery mode"""
        # In production, query from system contracts
        tcr = FVal('2.0')  # Total Collateral Ratio
        recovery_mode = tcr < FVal('1.5')
        
        return {
            'recovery_mode': recovery_mode,
            'total_collateral_ratio': str(tcr),
            'critical_threshold': '1.5',
            'message': 'System is in recovery mode - only improving operations allowed' if recovery_mode else 'System operating normally',
        }