"""Compound protocol service for async operations"""
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


class AsyncCompoundService(AsyncDeFiProtocolService):
    """Async service for Compound protocol operations
    
    Handles Compound V2 and V3 lending markets
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
        return f'compound-v{self.version}'
        
    async def get_balances(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[Asset, Balance]]:
        """Get current Compound balances (supplied and borrowed)"""
        balances = {}
        
        for address in addresses:
            address_balances = {}
            
            # Get supply positions
            supply_positions = await self._get_supply_positions(address)
            for asset, position in supply_positions.items():
                # cTokens represent supplied balance
                ctoken_balance = position.get('balance', ZERO)
                if ctoken_balance > ZERO:
                    address_balances[asset] = Balance(
                        amount=ctoken_balance,
                        usd_value=position.get('usd_value', ZERO),
                    )
            
            # Get borrow positions
            borrow_positions = await self._get_borrow_positions(address)
            for asset, position in borrow_positions.items():
                # Borrowed amounts are debts (negative)
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
        """Get all Compound positions for given addresses"""
        positions = {}
        
        for address in addresses:
            address_positions = []
            
            # Get supply positions
            supply = await self._get_supply_positions(address)
            for asset, data in supply.items():
                position = {
                    'type': 'supply',
                    'asset': asset.identifier,
                    'amount': str(data.get('balance', '0')),
                    'apy': str(data.get('apy', '0')),
                    'earned_interest': str(data.get('earned_interest', '0')),
                    'usd_value': str(data.get('usd_value', '0')),
                    'collateral_enabled': data.get('collateral_enabled', True),
                }
                address_positions.append(position)
                
            # Get borrow positions
            borrowing = await self._get_borrow_positions(address)
            for asset, data in borrowing.items():
                position = {
                    'type': 'borrow',
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
        
    async def _get_supply_positions(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[Asset, dict[str, Any]]:
        """Get supply positions for an address
        
        In production, this would query Compound's contracts or subgraph
        """
        # Mock data for demonstration
        # Real implementation would use web3 or graph queries
        return {
            Asset('USDC'): {
                'balance': FVal('2000'),
                'apy': FVal('0.0312'),  # 3.12%
                'earned_interest': FVal('62.40'),
                'usd_value': FVal('2062.40'),
                'collateral_enabled': True,
            },
            Asset('WETH'): {
                'balance': FVal('1.2'),
                'apy': FVal('0.0189'),  # 1.89%
                'earned_interest': FVal('0.0227'),
                'usd_value': FVal('1920'),  # Assuming $1600/ETH
                'collateral_enabled': True,
            },
        }
        
    async def _get_borrow_positions(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[Asset, dict[str, Any]]:
        """Get borrow positions for an address
        
        In production, this would query Compound's contracts or subgraph
        """
        # Mock data for demonstration
        return {
            Asset('DAI'): {
                'balance': FVal('1000'),
                'apy': FVal('0.0523'),  # 5.23%
                'accrued_interest': FVal('52.30'),
                'usd_value': FVal('1052.30'),
            },
        }
        
    async def get_account_liquidity(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, Any]:
        """Get account liquidity and borrow capacity
        
        Returns available liquidity and shortfall (if any)
        """
        # In production, query from Compound comptroller
        return {
            'total_collateral_usd': '3982.40',
            'total_borrow_usd': '1052.30',
            'available_borrow_usd': '1837.12',  # Based on collateral factors
            'borrow_utilization': '36.42%',
            'liquidation_threshold': '2388.80',  # 60% of collateral
            'shortfall': '0',  # Would be > 0 if underwater
        }
        
    async def get_claimable_comp(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[str, Any]]:
        """Get claimable COMP rewards"""
        rewards = {}
        
        for address in addresses:
            # In production, query from Compound comptroller
            rewards[address] = {
                'COMP': '25.75',
                'usd_value': '1287.50',
            }
            
        return rewards
        
    async def get_protocol_stats(self) -> dict[str, Any]:
        """Get Compound protocol statistics"""
        # In production, would query from Compound data provider
        return {
            'protocol': self.protocol_name,
            'version': self.version,
            'tvl': '5200000000',  # $5.2B
            'total_borrowed': '2100000000',  # $2.1B
            'active_markets': 15,
            'markets': [
                {
                    'asset': 'USDC',
                    'total_supply': '1500000000',
                    'total_borrow': '600000000',
                    'supply_apy': '3.12%',
                    'borrow_apy': '5.23%',
                    'utilization': '40.00%',
                    'collateral_factor': '0.80',  # 80%
                },
                {
                    'asset': 'WETH',
                    'total_supply': '800000',  # 800K ETH
                    'total_borrow': '300000',  # 300K ETH
                    'supply_apy': '1.89%',
                    'borrow_apy': '3.45%',
                    'utilization': '37.50%',
                    'collateral_factor': '0.75',  # 75%
                },
                {
                    'asset': 'WBTC',
                    'total_supply': '25000',  # 25K BTC
                    'total_borrow': '8000',  # 8K BTC
                    'supply_apy': '0.95%',
                    'borrow_apy': '2.15%',
                    'utilization': '32.00%',
                    'collateral_factor': '0.70',  # 70%
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
                    'seized_asset': event.asset.identifier,
                    'seized_amount': str(event.balance.amount),
                    'repay_asset': event.counterparty if hasattr(event, 'counterparty') else 'Unknown',
                    'liquidator': event.location_label if hasattr(event, 'location_label') else 'Unknown',
                })
                
        return liquidations
        
    async def get_market_info(
        self,
        asset: Asset,
    ) -> dict[str, Any]:
        """Get detailed market information for a specific asset"""
        # In production, query from Compound contracts
        return {
            'asset': asset.identifier,
            'ctoken_address': '0x...',  # cToken contract address
            'supply_rate': '0.0312',  # 3.12% APY
            'borrow_rate': '0.0523',  # 5.23% APY
            'exchange_rate': '0.021234',  # cToken to underlying rate
            'total_supply': '1500000000',
            'total_borrows': '600000000',
            'total_reserves': '15000000',
            'utilization_rate': '0.40',  # 40%
            'collateral_factor': '0.80',  # 80%
            'reserve_factor': '0.10',  # 10%
            'price_oracle': '1.00',  # Price in USD
        }