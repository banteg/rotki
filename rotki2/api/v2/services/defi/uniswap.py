"""Uniswap protocol service for async operations"""
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


class AsyncUniswapService(AsyncDeFiProtocolService):
    """Async service for Uniswap protocol operations
    
    Handles Uniswap V2 and V3 AMM positions and liquidity
    """
    
    def __init__(
        self,
        session: 'AsyncSession',
        http_client: 'AsyncHTTPClient | None' = None,
        history_repo: 'HistoryEventsRepository | None' = None,
        version: int = 3,  # Default to V3
    ):
        super().__init__(session, http_client, history_repo)
        self.version = version
        
    @property
    def protocol_name(self) -> str:
        """Return the protocol name"""
        return f'uniswap-v{self.version}'
        
    async def get_balances(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[Asset, Balance]]:
        """Get current Uniswap LP token balances"""
        balances = {}
        
        for address in addresses:
            address_balances = {}
            
            # Get LP positions
            lp_positions = await self._get_lp_positions(address)
            for pool_id, position in lp_positions.items():
                # Create LP token asset identifier
                lp_asset = Asset(f'UNI-V{self.version}-{pool_id}')
                
                total_value = position.get('total_value_usd', ZERO)
                if total_value > ZERO:
                    address_balances[lp_asset] = Balance(
                        amount=FVal(1),  # LP positions don't have traditional amounts
                        usd_value=total_value,
                    )
                    
            if address_balances:
                balances[address] = address_balances
                
        return balances
        
    async def get_positions(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[dict[str, Any]]]:
        """Get all Uniswap LP positions for given addresses"""
        positions = {}
        
        for address in addresses:
            address_positions = []
            
            # Get LP positions
            lp_positions = await self._get_lp_positions(address)
            for pool_id, data in lp_positions.items():
                position = {
                    'type': 'liquidity_pool',
                    'pool_id': pool_id,
                    'token0': data['token0']['symbol'],
                    'token1': data['token1']['symbol'],
                    'token0_amount': str(data['token0']['amount']),
                    'token1_amount': str(data['token1']['amount']),
                    'total_value_usd': str(data['total_value_usd']),
                    'fees_earned_usd': str(data.get('fees_earned_usd', '0')),
                    'impermanent_loss_usd': str(data.get('impermanent_loss_usd', '0')),
                    'pool_share': str(data.get('pool_share', '0')),
                }
                
                # V3 specific fields
                if self.version == 3:
                    position.update({
                        'lower_tick': data.get('lower_tick'),
                        'upper_tick': data.get('upper_tick'),
                        'in_range': data.get('in_range', True),
                        'liquidity': str(data.get('liquidity', '0')),
                    })
                    
                address_positions.append(position)
                
            if address_positions:
                positions[address] = address_positions
                
        return positions
        
    async def _get_lp_positions(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, dict[str, Any]]:
        """Get LP positions for an address
        
        In production, this would query Uniswap's subgraph
        """
        # Mock data for demonstration
        # Real implementation would use graph queries
        if self.version == 2:
            return {
                'ETH-USDC': {
                    'token0': {
                        'symbol': 'ETH',
                        'amount': FVal('2.5'),
                        'value_usd': FVal('4000'),
                    },
                    'token1': {
                        'symbol': 'USDC',
                        'amount': FVal('4000'),
                        'value_usd': FVal('4000'),
                    },
                    'total_value_usd': FVal('8000'),
                    'fees_earned_usd': FVal('250'),
                    'impermanent_loss_usd': FVal('-150'),
                    'pool_share': FVal('0.0025'),  # 0.25%
                },
            }
        else:  # V3
            return {
                'WETH-USDC-0.05%': {
                    'token0': {
                        'symbol': 'WETH',
                        'amount': FVal('1.8'),
                        'value_usd': FVal('2880'),
                    },
                    'token1': {
                        'symbol': 'USDC',
                        'amount': FVal('2880'),
                        'value_usd': FVal('2880'),
                    },
                    'total_value_usd': FVal('5760'),
                    'fees_earned_usd': FVal('180'),
                    'impermanent_loss_usd': FVal('-90'),
                    'pool_share': FVal('0.0018'),  # 0.18%
                    'lower_tick': -887220,
                    'upper_tick': 887220,
                    'in_range': True,
                    'liquidity': '1234567890123456789',
                },
                'UNI-WETH-0.3%': {
                    'token0': {
                        'symbol': 'UNI',
                        'amount': FVal('500'),
                        'value_usd': FVal('2500'),
                    },
                    'token1': {
                        'symbol': 'WETH',
                        'amount': FVal('1.5625'),
                        'value_usd': FVal('2500'),
                    },
                    'total_value_usd': FVal('5000'),
                    'fees_earned_usd': FVal('450'),
                    'impermanent_loss_usd': FVal('-200'),
                    'pool_share': FVal('0.0012'),  # 0.12%
                    'lower_tick': -75000,
                    'upper_tick': -65000,
                    'in_range': False,  # Price moved out of range
                    'liquidity': '9876543210987654321',
                },
            }
        
    async def get_fees_earned(
        self,
        address: ChecksumEvmAddress,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        """Get fees earned from LP positions"""
        if not self.history_repo:
            return {'total_fees_usd': '0', 'by_pool': {}}
            
        # Query fee collection events
        events = await self.history_repo.get_defi_events_by_protocol(
            protocol=self.protocol_name,
            account=address,
            start_timestamp=from_timestamp,
            end_timestamp=to_timestamp,
        )
        
        total_fees = FVal(0)
        fees_by_pool = {}
        
        for event in events:
            if hasattr(event, 'event_subtype') and event.event_subtype and 'fee' in event.event_subtype.value.lower():
                pool = event.extra_data.get('pool', 'Unknown') if hasattr(event, 'extra_data') else 'Unknown'
                if pool not in fees_by_pool:
                    fees_by_pool[pool] = FVal(0)
                    
                fee_amount = event.balance.usd_value or FVal(0)
                fees_by_pool[pool] += fee_amount
                total_fees += fee_amount
                
        return {
            'total_fees_usd': str(total_fees),
            'by_pool': {pool: str(amount) for pool, amount in fees_by_pool.items()},
        }
        
    async def get_impermanent_loss(
        self,
        address: ChecksumEvmAddress,
        pool_id: str,
    ) -> dict[str, Any]:
        """Calculate impermanent loss for a specific position
        
        In production, this would calculate based on entry price vs current price
        """
        # Mock calculation
        return {
            'pool_id': pool_id,
            'il_percentage': '-3.45%',
            'il_usd': '-275.50',
            'position_value_if_held': '8275.50',
            'current_position_value': '8000.00',
            'entry_price_ratio': '0.0004',  # token0/token1 at entry
            'current_price_ratio': '0.00045',  # token0/token1 now
        }
        
    async def get_protocol_stats(self) -> dict[str, Any]:
        """Get Uniswap protocol statistics"""
        # In production, would query from Uniswap subgraph
        if self.version == 2:
            return {
                'protocol': self.protocol_name,
                'version': self.version,
                'tvl': '3500000000',  # $3.5B
                'volume_24h': '1200000000',  # $1.2B
                'fees_24h': '3600000',  # $3.6M (0.3% of volume)
                'pool_count': 25000,
                'top_pools': [
                    {
                        'pair': 'WETH-USDC',
                        'tvl': '250000000',
                        'volume_24h': '150000000',
                        'fee_tier': '0.30%',
                    },
                    {
                        'pair': 'USDC-USDT',
                        'tvl': '180000000',
                        'volume_24h': '200000000',
                        'fee_tier': '0.30%',
                    },
                ],
            }
        else:  # V3
            return {
                'protocol': self.protocol_name,
                'version': self.version,
                'tvl': '5800000000',  # $5.8B
                'volume_24h': '2100000000',  # $2.1B
                'fees_24h': '2100000',  # $2.1M (variable fees)
                'pool_count': 12000,
                'top_pools': [
                    {
                        'pair': 'WETH-USDC',
                        'tvl': '450000000',
                        'volume_24h': '280000000',
                        'fee_tier': '0.05%',
                    },
                    {
                        'pair': 'WBTC-WETH',
                        'tvl': '320000000',
                        'volume_24h': '150000000',
                        'fee_tier': '0.30%',
                    },
                    {
                        'pair': 'USDC-USDT',
                        'tvl': '280000000',
                        'volume_24h': '350000000',
                        'fee_tier': '0.01%',
                    },
                ],
            }
            
    async def get_swap_history(
        self,
        address: ChecksumEvmAddress,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> list[dict[str, Any]]:
        """Get swap history for an address"""
        if not self.history_repo:
            return []
            
        # Query swap events
        events = await self.history_repo.get_defi_events_by_protocol(
            protocol=self.protocol_name,
            account=address,
            start_timestamp=from_timestamp,
            end_timestamp=to_timestamp,
        )
        
        swaps = []
        for event in events:
            if hasattr(event, 'event_type') and event.event_type.value == 'trade':
                swap = {
                    'timestamp': event.timestamp,
                    'token_in': event.asset.identifier,
                    'amount_in': str(event.balance.amount),
                    'token_out': event.counterparty if hasattr(event, 'counterparty') else 'Unknown',
                    'amount_out': str(event.extra_data.get('amount_out', '0')) if hasattr(event, 'extra_data') else '0',
                    'tx_hash': event.tx_hash if hasattr(event, 'tx_hash') else '',
                    'gas_used': str(event.extra_data.get('gas_used', '0')) if hasattr(event, 'extra_data') else '0',
                }
                swaps.append(swap)
                
        return swaps
        
    async def get_pool_info(
        self,
        pool_address: ChecksumEvmAddress,
    ) -> dict[str, Any]:
        """Get detailed information about a specific pool"""
        # In production, query from contracts or subgraph
        return {
            'address': pool_address,
            'token0': {
                'symbol': 'WETH',
                'address': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                'decimals': 18,
                'reserve': '125000',
            },
            'token1': {
                'symbol': 'USDC',
                'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                'decimals': 6,
                'reserve': '200000000',
            },
            'fee_tier': '0.05%' if self.version == 3 else '0.30%',
            'liquidity': '450000000',
            'sqrtPriceX96': '1234567890123456789012345678901234' if self.version == 3 else None,
            'tick': -202025 if self.version == 3 else None,
            'observation_index': 100 if self.version == 3 else None,
            'protocol_fee': '0' if self.version == 3 else None,
        }