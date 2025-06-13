"""Balances service for managing account balances"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotki2.api.v2.repositories.balance import BalanceRepository
from rotki2.api.v2.repositories.balance_source import (
    BlockchainBalanceSource,
    ExchangeBalanceSource,
    ManualBalanceSource,
)
from rotki2.api.v2.services.balance_aggregator import BalanceAggregator
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now, combine_dicts

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.exchanges.manager import ExchangeManager


class BalancesService:
    """Service for handling balance-related operations
    
    This service migrates the balance querying logic from RestAPI and Rotkehlchen
    to an async-first architecture.
    """

    def __init__(
        self,
        session: 'AsyncSession',
        chain_manager: 'ChainsAggregator | None' = None,
        exchange_manager: 'ExchangeManager | None' = None,
        notifier: 'RotkiNotifier | None' = None,
    ):
        self.session = session
        self.balance_repo = BalanceRepository(session)
        self.aggregator = BalanceAggregator()
        self.notifier = notifier
        self.chain_manager = chain_manager
        self.exchange_manager = exchange_manager

        # Set up balance sources
        if chain_manager:
            self.aggregator.add_source(BlockchainBalanceSource(chain_manager))
        if exchange_manager:
            self.aggregator.add_source(ExchangeBalanceSource(exchange_manager))

        # Always add manual balance source
        self.aggregator.add_source(ManualBalanceSource(self.balance_repo))

    async def query_all_balances(
        self,
        save_data: bool = False,
        ignore_errors: bool = True,
        ignore_cache: bool = False,
    ) -> dict[str, Any]:
        """Query all balances across blockchain and exchanges
        
        This migrates the logic from RestAPI.query_all_balances and 
        Rotkehlchen.query_balances.
        """
        # Send notification that balance query started
        if self.notifier:
            self.notifier.broadcast(
                event_type='balance_query_started',
                data={'query_type': 'all_balances'},
            )

        balances = {}
        liabilities = {}
        errors: list[str] = []
        
        # Query exchange balances
        if self.exchange_manager:
            exchange_balances, exchange_errors = await self._query_all_exchange_balances(
                ignore_cache=ignore_cache
            )
            balances = combine_dicts(balances, exchange_balances)
            errors.extend(exchange_errors)
        
        # Query blockchain balances
        if self.chain_manager:
            blockchain_balances, blockchain_errors = await self._query_blockchain_balances(
                blockchain=None,
                ignore_cache=ignore_cache,
            )
            balances = combine_dicts(balances, blockchain_balances)
            errors.extend(blockchain_errors)
        
        # Include manually tracked balances
        manual_balances = await self._get_manual_balances_dict()
        balances = combine_dicts(balances, manual_balances)
        
        # Include manually tracked liabilities
        manual_liabilities = await self._get_manual_liabilities_dict()
        liabilities = combine_dicts(liabilities, manual_liabilities)
        
        # Save balance snapshot if requested
        if save_data and (not errors or ignore_errors):
            await self._save_balance_snapshot(balances, liabilities)
        
        result = {
            'assets': balances,
            'liabilities': liabilities,
        }
        
        if errors and not ignore_errors:
            result['errors'] = errors
        
        # Send notification that balance query completed
        if self.notifier:
            self.notifier.broadcast(
                event_type='balance_query_completed',
                data={
                    'query_type': 'all_balances',
                    'success': len(errors) == 0,
                },
            )

        return result
    
    async def query_exchange_balances(
        self,
        location: Location | None = None,
        ignore_cache: bool = False,
        usd_value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
        """Query balances for specific exchange(s)
        
        This migrates the logic from RestAPI.query_exchange_balances.
        """
        if location is None:
            # Query all exchanges
            balances, errors = await self._query_all_exchange_balances(ignore_cache)
        else:
            # Query specific exchange
            balances, errors = await self._query_single_exchange_balances(
                location=location,
                ignore_cache=ignore_cache,
            )
        
        # Apply USD value threshold filter if provided
        if usd_value_threshold is not None:
            balances = self._filter_balances_by_usd_value(balances, usd_value_threshold)
        
        result = {'balances': balances}
        if errors:
            result['errors'] = errors
            
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

    async def get_manual_balances(
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

        db_balances = await self.balance_repo.find_by(**kwargs) if kwargs else await self.balance_repo.find_current_balances()

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

    async def _query_blockchain_balances(
        self,
        blockchain: Location | None = None,
        ignore_cache: bool = False,
    ) -> tuple[dict[Location, dict[Asset, Balance]], list[str]]:
        """Query blockchain balances"""
        if not self.chain_manager:
            return {}, []
            
        try:
            balances = await self.chain_manager.query_balances(
                blockchain=blockchain,
                ignore_cache=ignore_cache,
            )
            return balances, []
        except Exception as e:
            error_msg = f"Failed to query blockchain balances: {str(e)}"
            return {}, [error_msg]

    async def _query_all_exchange_balances(
        self,
        ignore_cache: bool = False,
    ) -> tuple[dict[Location, dict[Asset, Balance]], list[str]]:
        """Query balances from all connected exchanges"""
        if not self.exchange_manager:
            return {}, []
            
        all_balances = {}
        errors = []
        
        # Iterate through all connected exchanges
        for exchange in self.exchange_manager.iterate_exchanges():
            try:
                location_balances = await exchange.query_balances(
                    ignore_cache=ignore_cache,
                )
                # Handle multiple exchanges of same type
                if exchange.location in all_balances:
                    all_balances[exchange.location] = combine_dicts(
                        all_balances[exchange.location],
                        location_balances,
                    )
                else:
                    all_balances[exchange.location] = location_balances
            except Exception as e:
                error_msg = f"Failed to query {exchange.name} balances: {str(e)}"
                errors.append(error_msg)
                
        return all_balances, errors
    
    async def _query_single_exchange_balances(
        self,
        location: Location,
        ignore_cache: bool = False,
    ) -> tuple[dict[Location, dict[Asset, Balance]], list[str]]:
        """Query balances from a specific exchange type"""
        if not self.exchange_manager:
            return {}, []
            
        exchanges = self.exchange_manager.connected_exchanges.get(location, [])
        if not exchanges:
            return {}, [f"No {location} exchange connected"]
            
        combined_balances = {}
        errors = []
        
        for exchange in exchanges:
            try:
                balances = await exchange.query_balances(ignore_cache=ignore_cache)
                combined_balances = combine_dicts(combined_balances, balances)
            except Exception as e:
                error_msg = f"Failed to query {exchange.name} balances: {str(e)}"
                errors.append(error_msg)
                
        return {location: combined_balances} if combined_balances else {}, errors

    async def _get_manual_balances_dict(self) -> dict[Location, dict[Asset, Balance]]:
        """Get manually tracked balances as a dict"""
        manual_balances = await self.get_manual_balances()
        result = {}
        
        for balance in manual_balances:
            if balance.location not in result:
                result[balance.location] = {}
            
            result[balance.location][balance.asset] = Balance(
                amount=balance.amount,
                usd_value=balance.amount * balance.asset.price_in_usd(),
            )
            
        return result
    
    async def _get_manual_liabilities_dict(self) -> dict[Location, dict[Asset, Balance]]:
        """Get manually tracked liabilities as a dict"""
        # TODO: Implement manual liabilities when repository is available
        return {}
    
    async def _save_balance_snapshot(
        self,
        balances: dict[Location, dict[Asset, Balance]],
        liabilities: dict[Location, dict[Asset, Balance]],
    ) -> None:
        """Save a balance snapshot to the database"""
        timestamp = ts_now()
        
        # TODO: Implement balance snapshot saving
        # This would save to a balance_snapshots table
        pass
    
    def _filter_balances_by_usd_value(
        self,
        balances: dict[Location, dict[Asset, Balance]],
        threshold: FVal,
    ) -> dict[Location, dict[Asset, Balance]]:
        """Filter balances by USD value threshold"""
        filtered = {}
        
        for location, location_balances in balances.items():
            filtered_location = {}
            for asset, balance in location_balances.items():
                if balance.usd_value >= threshold:
                    filtered_location[asset] = balance
            
            if filtered_location:
                filtered[location] = filtered_location
                
        return filtered

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
