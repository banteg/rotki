"""Balances service for managing account balances"""
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

    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.exchanges.manager import ExchangeManager


class BalancesService:
    """Service for handling balance-related operations"""

    def __init__(
        self,
        session: 'Session',
        chain_manager: 'ChainsAggregator | None' = None,
        exchange_manager: 'ExchangeManager | None' = None,
        notifier: 'RotkiNotifier | None' = None,
    ):
        self.balance_repo = BalanceRepository(session)
        self.aggregator = BalanceAggregator()
        self.notifier = notifier

        # Set up balance sources
        if chain_manager:
            self.aggregator.add_source(BlockchainBalanceSource(chain_manager))
        if exchange_manager:
            self.aggregator.add_source(ExchangeBalanceSource(exchange_manager))

        # Always add manual balance source
        self.aggregator.add_source(ManualBalanceSource(self.balance_repo))

    def get_all_balances(self, save_data: bool = False) -> dict[str, Any]:
        """Get all balances across all locations"""
        # Send notification that balance query started
        if self.notifier:
            self.notifier.broadcast(
                event_type='balance_query_started',
                data={'query_type': 'all_balances'},
            )

        # Aggregate balances from all sources
        balance_sheet = self.aggregator.aggregate_balances()

        # TODO: Implement save_data functionality if needed

        result = {
            'assets': self.aggregator.serialize_balance_sheet(balance_sheet),
            'liabilities': {},
            'total_net_value': str(balance_sheet.get_total_net_value()),
        }

        # Send notification that balance query completed
        if self.notifier:
            self.notifier.broadcast(
                event_type='balance_query_completed',
                data={
                    'query_type': 'all_balances',
                    'total_net_value': result['total_net_value'],
                },
            )

        return result

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
            raise ValueError(f'Manual balance with id {identifier} not found')

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

    def edit_manual_balance(
        self,
        identifier: int,
        asset: Asset,
        amount: FVal,
        location: Location,
        tags: list[str] | None = None,
    ) -> ManuallyTrackedBalance:
        """Edit a manually tracked balance"""
        # Update the balance
        self.balance_repo.update(
            identifier=identifier,
            asset=asset.identifier,
            amount=str(amount),
            location=location.value,
            label='',  # Empty label for now
        )

        # Get and return the updated balance
        updated = self.balance_repo.get_by_id(identifier)
        return ManuallyTrackedBalance(
            identifier=updated.id,
            asset=Asset(updated.asset),
            label=updated.label or '',
            amount=FVal(updated.amount),
            location=Location.deserialize(updated.location),
            tags=tags or [],
        )

    def delete_manual_balance(self, identifier: int) -> bool:
        """Delete a manual balance"""
        return self.balance_repo.delete(identifier)

    def delete_manual_balances(self, identifiers: list[int]) -> int:
        """Delete multiple manual balances"""
        deleted_count = 0
        for identifier in identifiers:
            if self.balance_repo.delete(identifier):
                deleted_count += 1
        return deleted_count

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

    def _get_blockchain_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get blockchain balances only"""
        balance_sheet = self.aggregator.aggregate_balances()
        result = {}

        # Filter for blockchain locations only
        blockchain_locations = [
            Location.BITCOIN,
            Location.ETHEREUM,
            Location.ETHEREUM_BEACONCHAIN,
            Location.POLYGON_POS,
            Location.ARBITRUM_ONE,
            Location.OPTIMISM,
            Location.AVALANCHE,
            Location.GNOSIS,
            Location.KUSAMA,
            Location.POLKADOT,
        ]

        for location in blockchain_locations:
            location_balances = balance_sheet.get_location_balance(location)
            if location_balances:
                result[location] = location_balances

        return result

    def _get_exchange_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get exchange balances only"""
        balance_sheet = self.aggregator.aggregate_balances()
        result = {}

        # Get all locations and filter for exchanges
        for location in balance_sheet.locations:
            # Check if location is an exchange (not blockchain, bank, or manual)
            if location.is_exchange():
                location_balances = balance_sheet.get_location_balance(location)
                if location_balances:
                    result[location] = location_balances

        return result

    def _get_manual_balances(self) -> list[ManuallyTrackedBalance]:
        """Get manually tracked balances"""
        return self.get_manual_balances()

    def get_historical_balance_for_all_assets(
        self,
        timestamp: Timestamp,
    ) -> dict[str, dict[str, str]]:
        """Get historical balance for all assets at a timestamp"""
        # TODO: Implement proper historical balance query
        # For now, return current balances as placeholder
        current_balances = self.get_all_balances()

        result = {}
        for location, assets in current_balances['assets'].items():
            for asset_id, balance_data in assets.items():
                if asset_id not in result:
                    result[asset_id] = {
                        'amount': '0',
                        'usd_value': '0',
                        'locations': {},
                    }

                # Add to total
                result[asset_id]['amount'] = str(
                    FVal(result[asset_id]['amount']) + FVal(balance_data['amount']),
                )
                result[asset_id]['usd_value'] = str(
                    FVal(result[asset_id]['usd_value']) + FVal(balance_data['usd_value']),
                )

                # Add location details
                result[asset_id]['locations'][location] = balance_data

        return result

    def get_historical_asset_amounts(
        self,
        asset: Asset,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> list[dict[str, Any]]:
        """Get historical amounts for a single asset in a time range"""
        # TODO: Implement proper historical data query
        # For now, return simulated data points
        entries = []

        # Generate some sample data points
        interval = (to_timestamp - from_timestamp) // 10  # 10 data points
        if interval == 0:
            interval = 86400  # 1 day

        current_amount = FVal('1000')  # Starting amount

        for i in range(10):
            timestamp = from_timestamp + (i * interval)
            if timestamp > to_timestamp:
                break

            # Simulate some variation
            amount = current_amount * FVal(1 + (i * 0.1))
            usd_value = amount * FVal('1.5')  # Mock USD price

            entries.append({
                'timestamp': timestamp,
                'amount': str(amount),
                'usd_value': str(usd_value),
            })

        return entries

    def get_historical_netvalue(self) -> dict[str, Any]:
        """Get historical net value data"""
        # TODO: Implement proper historical net value query
        # For now, return simulated data
        import time

        current_time = int(time.time())
        times = []
        data = []

        # Generate 30 days of data
        for i in range(30):
            timestamp = current_time - (i * 86400)  # 1 day intervals
            times.append(timestamp)

            # Simulate net value changes
            base_value = 10000
            variation = (30 - i) * 100  # Increasing value over time
            data.append(str(base_value + variation))

        times.reverse()
        data.reverse()

        return {
            'times': times,
            'data': data,
        }
