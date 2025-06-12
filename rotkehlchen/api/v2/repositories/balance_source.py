"""Balance source interfaces and implementations for v2 API."""
from abc import ABC, abstractmethod
from typing import Protocol

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import Location


class BalanceSource(Protocol):
    """Protocol for balance sources (blockchain, exchange, manual, etc.)"""
    
    @abstractmethod
    def get_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get all balances from this source."""
        ...
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this balance source."""
        ...


class BlockchainBalanceSource:
    """Wrapper for blockchain balance queries via ChainsAggregator."""
    
    def __init__(self, chains_aggregator):
        self.chains = chains_aggregator
    
    def get_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Query all blockchain balances."""
        from collections import defaultdict
        
        # Query blockchain balances
        blockchain_result = self.chains.query_balances(
            blockchain=None,  # Query all blockchains
            ignore_cache=False,
        )
        
        # Convert to standard format
        balances = defaultdict(lambda: defaultdict(Balance))
        
        # Process per-account balances
        for blockchain, accounts_data in blockchain_result.per_account.items():
            location = Location.from_blockchain(blockchain)
            for account, account_balances in accounts_data.items():
                for asset, balance in account_balances.items():
                    if location not in balances:
                        balances[location] = {}
                    if asset not in balances[location]:
                        balances[location][asset] = Balance()
                    balances[location][asset] += balance
        
        return dict(balances)
    
    def get_source_name(self) -> str:
        return "blockchain"


class ExchangeBalanceSource:
    """Wrapper for exchange balance queries via ExchangeManager."""
    
    def __init__(self, exchange_manager):
        self.exchanges = exchange_manager
    
    def get_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Query all exchange balances."""
        from collections import defaultdict
        from rotkehlchen.fval import FVal
        
        balances = defaultdict(lambda: defaultdict(Balance))
        
        # Query all connected exchanges
        exchange_balances = self.exchanges.query_balances()
        
        for location_str, location_balances in exchange_balances.items():
            location = Location.deserialize(location_str)
            for asset_str, balance_data in location_balances.items():
                asset = Asset(asset_str)
                balance = Balance(
                    amount=FVal(balance_data['amount']),
                    usd_value=FVal(balance_data.get('usd_value', '0')),
                )
                balances[location][asset] = balance
        
        return dict(balances)
    
    def get_source_name(self) -> str:
        return "exchange"


class ManualBalanceSource:
    """Repository for manually tracked balances."""
    
    def __init__(self, balance_repository):
        self.repo = balance_repository
    
    def get_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get all manually tracked balances."""
        from collections import defaultdict
        from rotkehlchen.inquirer import Inquirer
        
        balances = defaultdict(dict)
        manual_balances = self.repo.find_current_balances()
        
        for mb in manual_balances:
            asset = Asset(mb.asset)
            # Calculate USD value
            usd_price = Inquirer.find_usd_price(asset)
            usd_value = FVal(mb.amount) * usd_price
            
            location = Location.deserialize(mb.location)
            balances[location][asset] = Balance(
                amount=FVal(mb.amount),
                usd_value=usd_value,
            )
        
        return dict(balances)
    
    def get_source_name(self) -> str:
        return "manual"