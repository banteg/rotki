"""Balance aggregation service for v2 API."""
from typing import Any

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.api.v2.repositories.balance_source import BalanceSource


class BalanceAggregator:
    """Service for aggregating balances from multiple sources."""
    
    def __init__(self):
        self.sources: list[BalanceSource] = []
    
    def add_source(self, source: BalanceSource) -> None:
        """Add a balance source to the aggregator."""
        self.sources.append(source)
    
    def remove_source(self, source_name: str) -> None:
        """Remove a balance source by name."""
        self.sources = [s for s in self.sources if s.get_source_name() != source_name]
    
    def aggregate_balances(self) -> BalanceSheet:
        """Aggregate balances from all sources into a single balance sheet."""
        balance_sheet = BalanceSheet()
        
        for source in self.sources:
            try:
                source_balances = source.get_balances()
                for location, assets in source_balances.items():
                    for asset, balance in assets.items():
                        balance_sheet.add(location, asset, balance)
            except Exception as e:
                # Log error but continue with other sources
                print(f"Error getting balances from {source.get_source_name()}: {e}")
        
        return balance_sheet
    
    def serialize_balance_sheet(self, sheet: BalanceSheet) -> dict[str, Any]:
        """Serialize balance sheet to API response format."""
        result = {}
        
        for location in sheet.locations:
            location_balances = {}
            for asset, balance in sheet.get_location_balance(location).items():
                location_balances[asset.identifier] = {
                    'amount': str(balance.amount),
                    'usd_value': str(balance.usd_value),
                }
            
            if location_balances:
                result[location.value] = location_balances
        
        return result