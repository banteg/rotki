"""Balance aggregation service for v2 API."""
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotki2.api.v2.repositories.balance_source import BalanceSource

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.types import Location


class LocationBalanceSheet:
    """Extended balance sheet that tracks balances by location."""

    def __init__(self):
        self._balances: dict[Location, dict[Asset, Balance]] = defaultdict(lambda: defaultdict(Balance))
        self._sheet = BalanceSheet()

    def add(self, location: 'Location', asset: 'Asset', balance: Balance) -> None:
        """Add a balance for a specific location and asset."""
        self._balances[location][asset] += balance
        self._sheet.assets[asset] += balance

    @property
    def locations(self) -> list['Location']:
        """Get all locations with balances."""
        return list(self._balances.keys())

    def get_location_balance(self, location: 'Location') -> dict['Asset', Balance]:
        """Get all balances for a specific location."""
        return dict(self._balances[location])

    def get_total_net_value(self) -> str:
        """Calculate total net value across all assets."""
        total = Balance()
        for asset_balances in self._balances.values():
            for balance in asset_balances.values():
                total += balance
        return str(total.usd_value)


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

    def aggregate_balances(self) -> LocationBalanceSheet:
        """Aggregate balances from all sources into a single balance sheet."""
        balance_sheet = LocationBalanceSheet()

        for source in self.sources:
            try:
                source_balances = source.get_balances()
                for location, assets in source_balances.items():
                    for asset, balance in assets.items():
                        balance_sheet.add(location, asset, balance)
            except Exception as e:
                # Log error but continue with other sources
                print(f'Error getting balances from {source.get_source_name()}: {e}')

        return balance_sheet

    def serialize_balance_sheet(self, sheet: LocationBalanceSheet) -> dict[str, Any]:
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
