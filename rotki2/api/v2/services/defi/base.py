"""Base class for DeFi protocol services"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import ChecksumEvmAddress, Timestamp

if TYPE_CHECKING:
    from rotki2.api.v2.repositories.history_events import HistoryEventsRepository
    from rotki2.utils.async_http_client import AsyncHTTPClient


class AsyncDeFiProtocolService(ABC):
    """Base class for async DeFi protocol services
    
    Provides common functionality for interacting with DeFi protocols
    including balance queries, position tracking, and yield calculations.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        http_client: 'AsyncHTTPClient | None' = None,
        history_repo: 'HistoryEventsRepository | None' = None,
    ):
        self.session = session
        self.http_client = http_client
        self.history_repo = history_repo
        
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Return the protocol name"""
        
    @abstractmethod
    async def get_balances(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[Asset, Balance]]:
        """Get current balances for given addresses
        
        Returns a mapping of address -> asset -> balance
        """
        
    @abstractmethod
    async def get_positions(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[dict[str, Any]]]:
        """Get all positions for given addresses
        
        Returns a mapping of address -> list of positions
        """
        
    async def get_historical_positions(
        self,
        addresses: list[ChecksumEvmAddress],
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> dict[ChecksumEvmAddress, list[dict[str, Any]]]:
        """Get historical positions from events
        
        This base implementation queries history events.
        Override for protocol-specific logic.
        """
        if not self.history_repo:
            return {}
            
        positions = {}
        
        for address in addresses:
            # Query protocol events for this address
            events = await self.history_repo.get_defi_events_by_protocol(
                protocol=self.protocol_name.lower(),
                account=address,
                start_timestamp=from_timestamp,
                end_timestamp=to_timestamp,
            )
            
            # Process events into positions
            # This is simplified - real implementation would reconstruct positions
            address_positions = []
            for event in events:
                position = {
                    'timestamp': event.timestamp,
                    'event_type': event.event_type.value,
                    'asset': event.asset.identifier,
                    'amount': str(event.balance.amount),
                    'usd_value': str(event.balance.usd_value),
                }
                address_positions.append(position)
                
            if address_positions:
                positions[address] = address_positions
                
        return positions
        
    async def get_yield_stats(
        self,
        addresses: list[ChecksumEvmAddress],
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> dict[ChecksumEvmAddress, dict[str, Any]]:
        """Calculate yield statistics for given addresses
        
        Returns yield earned, APY, and other metrics
        """
        # Base implementation - override for protocol-specific logic
        stats = {}
        
        for address in addresses:
            # Get events
            if self.history_repo:
                events = await self.history_repo.get_defi_events_by_protocol(
                    protocol=self.protocol_name.lower(),
                    account=address,
                    start_timestamp=from_timestamp,
                    end_timestamp=to_timestamp,
                )
                
                # Calculate basic stats
                total_yield = 0
                reward_events = [e for e in events if hasattr(e, 'event_subtype') and 
                               e.event_subtype and 'reward' in e.event_subtype.value.lower()]
                
                for event in reward_events:
                    if event.balance.usd_value:
                        total_yield += float(event.balance.usd_value)
                        
                stats[address] = {
                    'total_yield_usd': str(total_yield),
                    'reward_events': len(reward_events),
                    'period_days': (to_timestamp - from_timestamp) / 86400,
                }
                
        return stats
        
    async def get_protocol_stats(self) -> dict[str, Any]:
        """Get protocol-wide statistics
        
        Override this method for protocol-specific stats
        """
        return {
            'protocol': self.protocol_name,
            'tvl': '0',
            'active_users': 0,
        }