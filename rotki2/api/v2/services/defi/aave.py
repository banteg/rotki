"""Aave protocol service for async operations"""
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


class AsyncAaveService(AsyncDeFiProtocolService):
    """Async service for Aave protocol operations
    
    Handles Aave V2 and V3 lending positions, borrowing, and rewards
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
        return f'aave-v{self.version}'
        
    async def get_balances(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[Asset, Balance]]:
        """Get current Aave balances (supplied and borrowed)"""
        balances = {}
        
        for address in addresses:
            address_balances = {}
            
            # Get lending positions
            lending_positions = await self._get_lending_positions(address)
            for asset, position in lending_positions.items():
                # aTokens represent supplied balance
                atoken_balance = position.get('balance', ZERO)
                if atoken_balance > ZERO:
                    address_balances[asset] = Balance(
                        amount=atoken_balance,
                        usd_value=position.get('usd_value', ZERO),
                    )
            
            # Get borrowing positions
            borrowing_positions = await self._get_borrowing_positions(address)
            for asset, position in borrowing_positions.items():
                # Debt tokens represent borrowed balance (negative)
                debt_balance = position.get('balance', ZERO)
                if debt_balance > ZERO:
                    # Store as negative balance to indicate debt
                    debt_asset = Asset(f'{asset.identifier}_DEBT')
                    address_balances[debt_asset] = Balance(
                        amount=-debt_balance,
                        usd_value=-position.get('usd_value', ZERO),
                    )
                    
            if address_balances:
                balances[address] = address_balances
                
        return balances
        
    async def get_positions(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[dict[str, Any]]]:
        """Get all Aave positions for given addresses"""
        positions = {}
        
        for address in addresses:
            address_positions = []
            
            # Get lending positions
            lending = await self._get_lending_positions(address)
            for asset, data in lending.items():
                position = {
                    'type': 'lending',
                    'asset': asset.identifier,
                    'amount': str(data.get('balance', '0')),
                    'apy': str(data.get('apy', '0')),
                    'earned_interest': str(data.get('earned_interest', '0')),
                    'usd_value': str(data.get('usd_value', '0')),
                }
                address_positions.append(position)
                
            # Get borrowing positions
            borrowing = await self._get_borrowing_positions(address)
            for asset, data in borrowing.items():
                position = {
                    'type': 'borrowing',
                    'asset': asset.identifier,
                    'amount': str(data.get('balance', '0')),
                    'apy': str(data.get('apy', '0')),
                    'accrued_interest': str(data.get('accrued_interest', '0')),
                    'usd_value': str(data.get('usd_value', '0')),
                }
                address_positions.append(position)
                
            if address_positions:
                positions[address] = address_positions
                
        return positions
        
    async def _get_lending_positions(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[Asset, dict[str, Any]]:
        """Get lending positions for an address
        
        In production, this would query Aave's contracts or subgraph
        """
        # Mock data for demonstration
        # Real implementation would use web3 or graph queries
        return {
            Asset('USDC'): {
                'balance': FVal('1000'),
                'apy': FVal('0.0234'),  # 2.34%
                'earned_interest': FVal('23.40'),
                'usd_value': FVal('1023.40'),
            },
            Asset('ETH'): {
                'balance': FVal('0.5'),
                'apy': FVal('0.0156'),  # 1.56%
                'earned_interest': FVal('0.0078'),
                'usd_value': FVal('800'),  # Assuming $1600/ETH
            },
        }
        
    async def _get_borrowing_positions(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[Asset, dict[str, Any]]:
        """Get borrowing positions for an address
        
        In production, this would query Aave's contracts or subgraph
        """
        # Mock data for demonstration
        return {
            Asset('DAI'): {
                'balance': FVal('500'),
                'apy': FVal('0.0456'),  # 4.56%
                'accrued_interest': FVal('22.80'),
                'usd_value': FVal('522.80'),
            },
        }
        
    async def get_health_factor(
        self,
        address: ChecksumEvmAddress,
    ) -> FVal:
        """Get the health factor for an address
        
        Health factor = Total Collateral in ETH * Liquidation Threshold / Total Borrows in ETH
        """
        # In production, query from Aave contracts
        # For now, return mock healthy value
        return FVal('1.85')  # > 1 means healthy
        
    async def get_claimable_rewards(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[str, Any]]:
        """Get claimable rewards (stkAAVE rewards)"""
        rewards = {}
        
        for address in addresses:
            # In production, query rewards from incentives controller
            rewards[address] = {
                'stkAAVE': '12.5',
                'usd_value': '1250',
            }
            
        return rewards
        
    async def get_protocol_stats(self) -> dict[str, Any]:
        """Get Aave protocol statistics"""
        # In production, would query from Aave data provider
        return {
            'protocol': self.protocol_name,
            'version': self.version,
            'tvl': '12500000000',  # $12.5B
            'total_borrowed': '4200000000',  # $4.2B
            'active_users': 125000,
            'markets': [
                {
                    'asset': 'USDC',
                    'total_supplied': '3500000000',
                    'total_borrowed': '1200000000',
                    'supply_apy': '2.34%',
                    'borrow_apy': '4.56%',
                    'utilization': '34.29%',
                },
                {
                    'asset': 'ETH',
                    'total_supplied': '2100000',  # 2.1M ETH
                    'total_borrowed': '850000',  # 850K ETH
                    'supply_apy': '1.56%',
                    'borrow_apy': '2.89%',
                    'utilization': '40.48%',
                },
            ],
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
                    'collateral_asset': event.asset.identifier,
                    'collateral_amount': str(event.balance.amount),
                    'debt_asset': event.counterparty if hasattr(event, 'counterparty') else 'Unknown',
                    'liquidator': event.location_label if hasattr(event, 'location_label') else 'Unknown',
                })
                
        return liquidations