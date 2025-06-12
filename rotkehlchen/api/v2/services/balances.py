"""Balances service for managing account balances"""
from collections import defaultdict
from typing import Any

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp


class BalancesService:
    """Service for handling balance-related operations"""

    def __init__(
        self,
        db_service: DatabaseService,
        chain_manager: ChainsAggregator | None = None,
        exchange_manager: ExchangeManager | None = None,
    ):
        self.db = db_service
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
            balances.add(
                balance.location,
                balance.asset,
                Balance(amount=balance.amount, usd_value=balance.usd_value),
            )

        return {
            'assets': self._serialize_balance_sheet(balances),
            'liabilities': {},
            'total_net_value': str(balances.get_total_net_value()),
        }

    def _get_blockchain_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get balances from blockchain accounts"""
        balances = defaultdict(lambda: defaultdict(Balance))

        # This is simplified - real implementation would query each blockchain
        accounts = self.db.get_blockchain_accounts()

        for account in accounts:
            # Mock balance for demonstration
            location = Location.ETHEREUM  # Would map from account.blockchain
            asset = Asset('ETH')
            amount = FVal('1.5')
            usd_value = FVal('3000')

            balances[location][asset] = Balance(amount=amount, usd_value=usd_value)

        return dict(balances)

    def _get_exchange_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get balances from exchanges"""
        balances = defaultdict(lambda: defaultdict(Balance))

        # This is simplified - real implementation would query each exchange
        credentials = self.db.get_user_credentials()

        for cred in credentials:
            # Mock balance for demonstration
            location = Location(cred.location)
            asset = Asset('BTC')
            amount = FVal('0.5')
            usd_value = FVal('25000')

            balances[location][asset] = Balance(amount=amount, usd_value=usd_value)

        return dict(balances)

    def _get_manual_balances(self) -> list[ManuallyTrackedBalance]:
        """Get manually tracked balances"""
        # In real implementation, would query from database
        return []

    def add_manual_balance(
        self,
        asset: Asset,
        amount: FVal,
        location: Location,
        tags: list[str] | None = None,
    ) -> ManuallyTrackedBalance:
        """Add a manually tracked balance"""
        balance = ManuallyTrackedBalance(
            identifier=-1,  # Will be set by DB
            asset=asset,
            label='',
            amount=amount,
            location=location,
            tags=tags or [],
        )

        # In real implementation, would save to database
        return balance

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
        # Simplified implementation
        return {
            'timestamp': timestamp,
            'balances': {},
            'total_net_value': '0',
        }
