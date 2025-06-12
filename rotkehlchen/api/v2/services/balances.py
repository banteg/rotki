"""Balances service for managing account balances"""
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.v2.repositories.balance import BalanceRepository
from rotkehlchen.api.v2.repositories.balance_source import (
    BlockchainBalanceSource,
    ExchangeBalanceSource,
    ManualBalanceSource,
)
from rotkehlchen.api.v2.services.balance_aggregator import BalanceAggregator
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from sqlmodel import Session
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.exchanges.manager import ExchangeManager


class BalancesService:
    """Service for handling balance-related operations"""

    def __init__(
        self,
        session: 'Session',
        chain_manager: 'ChainsAggregator | None' = None,
        exchange_manager: 'ExchangeManager | None' = None,
    ):
        self.balance_repo = BalanceRepository(session)
        self.aggregator = BalanceAggregator()
        
        # Set up balance sources
        if chain_manager:
            self.aggregator.add_source(BlockchainBalanceSource(chain_manager))
        if exchange_manager:
            self.aggregator.add_source(ExchangeBalanceSource(exchange_manager))
        
        # Always add manual balance source
        self.aggregator.add_source(ManualBalanceSource(self.balance_repo))

    def get_all_balances(self, save_data: bool = False) -> dict[str, Any]:
        """Get all balances across all locations"""
        # Aggregate balances from all sources
        balance_sheet = self.aggregator.aggregate_balances()
        
        # TODO: Implement save_data functionality if needed
        
        return {
            'assets': self.aggregator.serialize_balance_sheet(balance_sheet),
            'liabilities': {},
            'total_net_value': str(balance_sheet.get_total_net_value()),
        }

    def get_balances_by_location(self, location: Location) -> dict[str, Any]:
        """Get balances for a specific location"""
        balance_sheet = self.aggregator.aggregate_balances()
        location_balances = balance_sheet.get_location_balance(location)
        
        result = {}
        for asset, balance in location_balances.items():
            result[asset.identifier] = {
                'amount': str(balance.amount),
                'usd_value': str(balance.usd_value),
            }
        
        return result
    
    def get_balances_by_asset(self, asset: Asset) -> dict[str, Any]:
        """Get balances for a specific asset across all locations"""
        balance_sheet = self.aggregator.aggregate_balances()
        
        result = {}
        for location in balance_sheet.locations:
            location_balances = balance_sheet.get_location_balance(location)
            if asset in location_balances:
                balance = location_balances[asset]
                result[location.value] = {
                    'amount': str(balance.amount),
                    'usd_value': str(balance.usd_value),
                }
        
        return result

    def add_manual_balance(
        self,
        asset: Asset,
        amount: FVal,
        location: Location,
        label: str = '',
        tags: list[str] | None = None,
    ) -> ManuallyTrackedBalance:
        """Add a manually tracked balance"""
        # Use repository to create the balance
        balance = self.balance_repo.update_balance(
            asset=asset.identifier,
            label=label,
            location=location.serialize(),
            amount=str(amount),
            usd_value='0',  # Will be calculated on retrieval
        )
        
        # TODO: Handle tags via a tag repository
        
        return ManuallyTrackedBalance(
            identifier=balance.id,
            asset=asset,
            label=label,
            amount=amount,
            location=location,
            tags=tags or [],
        )
    
    def update_manual_balance(
        self,
        identifier: int,
        amount: FVal | None = None,
        label: str | None = None,
        tags: list[str] | None = None,
    ) -> ManuallyTrackedBalance:
        """Update an existing manual balance"""
        balance = self.balance_repo.get(identifier)
        if not balance:
            raise ValueError(f"Manual balance with id {identifier} not found")
        
        if amount is not None:
            balance.amount = str(amount)
        if label is not None:
            balance.label = label
        
        updated = self.balance_repo.update(balance)
        
        # TODO: Handle tags update via a tag repository
        
        return ManuallyTrackedBalance(
            identifier=updated.id,
            asset=Asset(updated.asset),
            label=updated.label,
            amount=FVal(updated.amount),
            location=Location.deserialize(updated.location),
            tags=tags or [],
        )
    
    def delete_manual_balance(self, identifier: int) -> bool:
        """Delete a manual balance"""
        return self.balance_repo.delete(identifier)

    def get_manual_balances(
        self,
        asset: Asset | None = None,
        label: str | None = None,
        location: Location | None = None,
    ) -> list[ManuallyTrackedBalance]:
        """Get manually tracked balances with optional filtering"""
        kwargs = {}
        if asset:
            kwargs['asset'] = asset.identifier
        if label:
            kwargs['label'] = label
        if location:
            kwargs['location'] = location.serialize()
        
        db_balances = self.balance_repo.find_by(**kwargs) if kwargs else self.balance_repo.find_current_balances()
        
        result = []
        for db_balance in db_balances:
            result.append(ManuallyTrackedBalance(
                identifier=db_balance.id,
                asset=Asset(db_balance.asset),
                label=db_balance.label,
                amount=FVal(db_balance.amount),
                location=Location.deserialize(db_balance.location),
                tags=[],  # TODO: Query tags separately
            ))
        
        return result

    def get_historical_balance(
        self,
        timestamp: Timestamp,
        asset: Asset | None = None,
        location: Location | None = None,
    ) -> dict[str, Any]:
        """Get historical balance at specific timestamp"""
        # TODO: Implement using a proper historical balance repository
        # For now, return current balances as a placeholder
        current_balances = self.get_all_balances()
        
        # Filter by asset/location if provided
        if asset or location:
            filtered = {}
            for loc_str, assets in current_balances['assets'].items():
                if location and Location.deserialize(loc_str) != location:
                    continue
                
                if asset:
                    if asset.identifier in assets:
                        if loc_str not in filtered:
                            filtered[loc_str] = {}
                        filtered[loc_str][asset.identifier] = assets[asset.identifier]
                else:
                    filtered[loc_str] = assets
            
            return {
                'timestamp': timestamp,
                'balances': filtered,
                'total_net_value': current_balances['total_net_value'],
            }
        
        return {
            'timestamp': timestamp,
            'balances': current_balances['assets'],
            'total_net_value': current_balances['total_net_value'],
        }
