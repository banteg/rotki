"""Balances service for managing account balances"""
from collections import defaultdict
from typing import Any

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import Location, Timestamp


class BalancesService:
    """Service for handling balance-related operations"""

    def __init__(
        self,
        db_connection: DBConnection,
        chain_manager: ChainsAggregator | None = None,
        exchange_manager: ExchangeManager | None = None,
    ):
        self.db_connection = db_connection
        self.chain_manager = chain_manager
        self.exchange_manager = exchange_manager

    def get_all_balances(self, save_data: bool = False) -> dict[str, Any]:
        """Get all balances across all locations"""
        balances = BalanceSheet()

        # Get blockchain balances
        if self.chain_manager:
            blockchain_balances = self._get_blockchain_balances()
            for location, assets in blockchain_balances.items():
                for asset, balance in assets.items():
                    balances.add(location, asset, balance)

        # Get exchange balances
        if self.exchange_manager:
            exchange_balances = self._get_exchange_balances()
            for location, assets in exchange_balances.items():
                for asset, balance in assets.items():
                    balances.add(location, asset, balance)

        # Get manually tracked balances
        manual_balances = self._get_manual_balances()
        for balance in manual_balances:
            # Calculate USD value for manually tracked balance
            usd_price = Inquirer.find_usd_price(balance.asset)
            usd_value = balance.amount * usd_price
            balances.add(
                balance.location,
                balance.asset,
                Balance(amount=balance.amount, usd_value=usd_value),
            )

        return {
            'assets': self._serialize_balance_sheet(balances),
            'liabilities': {},
            'total_net_value': str(balances.get_total_net_value()),
        }

    def _get_blockchain_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get balances from blockchain accounts"""
        if not self.chain_manager:
            return {}

        # Query blockchain balances using the chain aggregator
        blockchain_result = self.chain_manager.query_balances(
            blockchain=None,  # Query all blockchains
            ignore_cache=False,
        )

        # Convert BlockchainBalances to our format
        balances = defaultdict(lambda: defaultdict(Balance))

        # Process per-account balances
        for blockchain, accounts_data in blockchain_result.per_account.items():
            # Map blockchain to location
            location = Location.from_blockchain(blockchain)
            for account, account_balances in accounts_data.items():
                for asset, balance in account_balances.items():
                    if location not in balances:
                        balances[location] = {}
                    if asset not in balances[location]:
                        balances[location][asset] = Balance()
                    balances[location][asset] += balance

        return dict(balances)

    def _get_exchange_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get balances from exchanges"""
        if not self.exchange_manager:
            return {}

        balances = defaultdict(lambda: defaultdict(Balance))

        # Query all connected exchanges
        exchange_balances = self.exchange_manager.query_balances()

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

    def _get_manual_balances(self) -> list[ManuallyTrackedBalance]:
        """Get manually tracked balances"""
        with self.db_connection.read_ctx() as cursor:
            cursor.execute(
                'SELECT id, asset, label, amount, location, category FROM manually_tracked_balances',
            )
            balances = []
            for row in cursor:
                balance = ManuallyTrackedBalance(
                    identifier=row[0],
                    asset=Asset(row[1]),
                    label=row[2],
                    amount=FVal(row[3]),
                    location=Location.deserialize(row[4]),
                    tags=[],  # Tags would need to be queried separately
                )
                balances.append(balance)
            return balances

    def add_manual_balance(
        self,
        asset: Asset,
        amount: FVal,
        location: Location,
        label: str = '',
        tags: list[str] | None = None,
    ) -> ManuallyTrackedBalance:
        """Add a manually tracked balance"""
        with self.db_connection.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT INTO manually_tracked_balances (asset, label, amount, location, category) '
                'VALUES (?, ?, ?, ?, ?)',
                (asset.identifier, label, str(amount), location.serialize(), 'A'),
            )
            balance_id = write_cursor.lastrowid

            # Add tag associations if provided
            if tags:
                for tag in tags:
                    write_cursor.execute(
                        'INSERT INTO tag_mappings (object_reference, tag_name) VALUES (?, ?)',
                        (f'manually_tracked_balance_{balance_id}', tag),
                    )

            return ManuallyTrackedBalance(
                identifier=balance_id,
                asset=asset,
                label=label,
                amount=amount,
                location=location,
                tags=tags or [],
            )

    def _serialize_balance_sheet(self, sheet: BalanceSheet) -> dict[str, Any]:
        """Serialize balance sheet to API response format"""
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

    def get_historical_balance(
        self,
        timestamp: Timestamp,
        asset: Asset | None = None,
        location: Location | None = None,
    ) -> dict[str, Any]:
        """Get historical balance at specific timestamp"""
        # Query historical timed_balances from database
        query = 'SELECT time, location, currency, amount, usd_value FROM timed_balances WHERE time = ?'
        params = [timestamp]

        if asset:
            query += ' AND currency = ?'
            params.append(asset.identifier)

        if location:
            query += ' AND location = ?'
            params.append(location.serialize())

        balances = defaultdict(lambda: defaultdict(dict))
        total_usd_value = FVal('0')

        with self.db_connection.read_ctx() as cursor:
            cursor.execute(query, params)
            for row in cursor:
                location_str = row[1]
                asset_str = row[2]
                amount = FVal(row[3])
                usd_value = FVal(row[4])

                balances[location_str][asset_str] = {
                    'amount': str(amount),
                    'usd_value': str(usd_value),
                }
                total_usd_value += usd_value

        return {
            'timestamp': timestamp,
            'balances': dict(balances),
            'total_net_value': str(total_usd_value),
        }
