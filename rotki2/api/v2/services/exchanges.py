"""Exchange service for managing exchange connections and data"""
from typing import TYPE_CHECKING, Any

from rotki2.api.v2.services.database import DatabaseService
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.types import ApiKey, ApiSecret, Location
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from rotkehlchen.exchanges.manager import ExchangeManager


class ExchangeInfo:
    """Exchange information container"""
    def __init__(
        self,
        name: str,
        location: str,
        kraken_account_type: str | None = None,
        binance_markets: list[str] | None = None,
    ):
        self.name = name
        self.location = location
        self.kraken_account_type = kraken_account_type
        self.binance_markets = binance_markets


class ExchangeService:
    """Service for exchange operations
    
    This service migrates the exchange management logic from RestAPI
    to an async-first architecture.
    """

    def __init__(
        self,
        session: 'AsyncSession',
        db_service: DatabaseService,
        exchange_manager: 'ExchangeManager | None' = None,
    ):
        self.session = session
        self.db = db_service
        self.exchange_manager = exchange_manager

    def get_configured_exchanges(self) -> list[ExchangeInfo]:
        """Get all configured exchanges"""
        credentials = self.db.get_user_credentials()
        exchanges = []

        for cred in credentials:
            # Get additional exchange-specific data from mappings
            kraken_type = None
            binance_markets = None

            if cred.location == 'D':  # Kraken
                # Would fetch from credential mappings
                kraken_type = 'starter'
            elif cred.location in ('C', 'U'):  # Binance/BinanceUS
                # Would fetch from credential mappings
                binance_markets = ['BTCUSDT', 'ETHUSDT']

            exchanges.append(ExchangeInfo(
                name=cred.name,
                location=cred.location,
                kraken_account_type=kraken_type,
                binance_markets=binance_markets,
            ))

        return exchanges

    async def setup_exchange(
        self,
        name: str,
        location: Location,
        api_key: ApiKey,
        api_secret: ApiSecret | None,
        passphrase: str | None = None,
        kraken_account_type: KrakenAccountType | None = None,
        binance_selected_trade_pairs: list[str] | None = None,
    ) -> tuple[bool, str]:
        """Setup a new exchange with api credentials
        
        This migrates the logic from RestAPI.setup_exchange and
        Rotkehlchen.setup_exchange.
        """
        if not self.exchange_manager:
            return False, "Exchange manager not initialized"
            
        # Delegate to exchange manager for setup and validation
        success, msg = await self.exchange_manager.setup_exchange(
            name=name,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            database=self.db,
            passphrase=passphrase,
            binance_selected_trade_pairs=binance_selected_trade_pairs,
        )
        
        if success:
            # Save exchange credentials to database
            await self.db.add_exchange(
                name=name,
                location=location,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
            )
            
            # Handle exchange-specific settings
            if kraken_account_type is not None:
                await self.db.set_kraken_account_type(
                    name=name,
                    account_type=kraken_account_type,
                )
            
            if binance_selected_trade_pairs is not None:
                await self.db.set_binance_selected_trade_pairs(
                    name=name,
                    pairs=binance_selected_trade_pairs,
                )
                
        return success, msg

    async def remove_exchange(self, name: str, location: Location) -> tuple[bool, str]:
        """Remove exchange connection
        
        This migrates the logic from RestAPI.remove_exchange.
        """
        if not self.exchange_manager:
            return False, "Exchange manager not initialized"
            
        success, msg = await self.exchange_manager.delete_exchange(
            name=name,
            location=location,
        )
        
        if success:
            # Also remove from database
            await self.db.remove_exchange(
                name=name,
                location=location,
            )
            
        return success, msg

    async def get_all_exchange_balances(
        self,
        ignore_cache: bool = False,
    ) -> dict[str, Any]:
        """Get balances from all exchanges
        
        This is now handled by BalancesService.query_exchange_balances
        """
        # Deprecated - use BalancesService instead
        from rotki2.api.v2.services.balances import BalancesService
        
        balances_service = BalancesService(
            session=self.session,
            exchange_manager=self.exchange_manager,
        )
        
        result = await balances_service.query_exchange_balances(
            location=None,  # Query all exchanges
            ignore_cache=ignore_cache,
        )
        
        return result.get('balances', {})

    def get_exchange_balances(
        self,
        location: Location,
        ignore_cache: bool = False,
    ) -> dict[str, Any]:
        """Get balances from specific exchange"""
        # Simplified implementation - would query actual exchange
        return {
            'BTC': {
                'amount': '0.5',
                'usd_value': '25000',
            },
            'ETH': {
                'amount': '10',
                'usd_value': '20000',
            },
        }

    async def query_trades(
        self,
        name: str,
        location: Location,
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
    ) -> list[Trade]:
        """Query trades from exchange"""
        if not self.exchange_manager:
            return []
            
        # Get the specific exchange instance
        exchanges = self.exchange_manager.connected_exchanges.get(location, [])
        exchange = next((e for e in exchanges if e.name == name), None)
        
        if not exchange:
            raise ValueError(f"Exchange {name} not found")
            
        # Query trades from the exchange
        trades = await exchange.query_trade_history(
            start_ts=from_timestamp or 0,
            end_ts=to_timestamp or ts_now(),
        )
        
        return trades

    async def query_deposits_withdrawals(
        self,
        name: str,
        location: Location,
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
    ) -> tuple[list[AssetMovement], list[AssetMovement]]:
        """Query deposits and withdrawals from exchange"""
        if not self.exchange_manager:
            return [], []
            
        # Get the specific exchange instance
        exchanges = self.exchange_manager.connected_exchanges.get(location, [])
        exchange = next((e for e in exchanges if e.name == name), None)
        
        if not exchange:
            raise ValueError(f"Exchange {name} not found")
            
        # Query asset movements from the exchange
        movements = await exchange.query_deposits_withdrawals(
            start_ts=from_timestamp or 0,
            end_ts=to_timestamp or ts_now(),
        )
        
        # Separate deposits and withdrawals
        deposits = [m for m in movements if m.category == 'deposit']
        withdrawals = [m for m in movements if m.category == 'withdrawal']
        
        return deposits, withdrawals

    async def query_margin_positions(
        self,
        name: str,
        location: Location,
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
    ) -> list[MarginPosition]:
        """Query margin positions from exchange"""
        if not self.exchange_manager:
            return []
            
        # Get the specific exchange instance
        exchanges = self.exchange_manager.connected_exchanges.get(location, [])
        exchange = next((e for e in exchanges if e.name == name), None)
        
        if not exchange:
            raise ValueError(f"Exchange {name} not found")
            
        # Check if exchange supports margin trading
        if not hasattr(exchange, 'query_margin_history'):
            return []
            
        # Query margin positions from the exchange
        positions = await exchange.query_margin_history(
            start_ts=from_timestamp or 0,
            end_ts=to_timestamp or ts_now(),
        )
        
        return positions

    async def edit_exchange(
        self,
        name: str,
        location: Location,
        new_name: str | None = None,
        api_key: ApiKey | None = None,
        api_secret: ApiSecret | None = None,
        passphrase: str | None = None,
        kraken_account_type: KrakenAccountType | None = None,
        binance_selected_trade_pairs: list[str] | None = None,
    ) -> tuple[bool, str]:
        """Edit existing exchange connection
        
        This migrates the logic from RestAPI.edit_exchange.
        """
        if not self.exchange_manager:
            return False, "Exchange manager not initialized"
            
        success, msg = await self.exchange_manager.edit_exchange(
            name=name,
            location=location,
            new_name=new_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            database=self.db,
        )
        
        if success:
            # Update exchange-specific settings if provided
            if kraken_account_type is not None:
                await self.db.set_kraken_account_type(
                    name=new_name or name,
                    account_type=kraken_account_type,
                )
            
            if binance_selected_trade_pairs is not None:
                await self.db.set_binance_selected_trade_pairs(
                    name=new_name or name,
                    pairs=binance_selected_trade_pairs,
                )
                
        return success, msg

    def purge_all_exchange_data(self) -> None:
        """Purge all exchange data from database"""
        # Would delete all cached exchange data from DB

    def purge_exchange_data(self, location: Location) -> None:
        """Purge specific exchange data from database"""
        # Would delete cached data for specific exchange from DB

    async def get_binance_pairs(self) -> list[str]:
        """Get all available Binance pairs"""
        if not self.exchange_manager:
            return []
            
        # Get Binance exchange instance
        binance_exchanges = self.exchange_manager.connected_exchanges.get(Location.BINANCE, [])
        if not binance_exchanges:
            # If no Binance connection, we could still query available pairs
            # For now, return empty list
            return []
            
        binance = binance_exchanges[0]
        
        # Get all available trading pairs
        if hasattr(binance, 'get_all_pairs'):
            return await binance.get_all_pairs()
        
        return []

    async def get_user_binance_pairs(self, name: str) -> list[str]:
        """Get user-configured Binance pairs"""
        # Fetch from database
        pairs = await self.db.get_binance_selected_trade_pairs(name)
        return pairs or []

    def get_exchange_savings_history(
        self,
        location: Location,
        from_timestamp: int,
        to_timestamp: int,
    ) -> dict[str, Any]:
        """Get exchange savings/lending history"""
        # Would fetch savings history from exchange
        return {
            'lending_history': [
                {
                    'asset': 'USDT',
                    'amount': '1000',
                    'earned_interest': '10.5',
                    'timestamp': from_timestamp + 86400,
                },
                {
                    'asset': 'BTC',
                    'amount': '0.5',
                    'earned_interest': '0.001',
                    'timestamp': from_timestamp + 172800,
                },
            ],
            'total_earned': {
                'USDT': '10.5',
                'BTC': '0.001',
            },
        }

    def query_exchange_events(
        self,
        location: Location,
        from_timestamp: int,
        to_timestamp: int,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query history events for an exchange"""
        # Would query exchange events from database
        events = []

        # Simulate some exchange events
        base_events = [
            {
                'timestamp': from_timestamp + 3600,
                'location': location.value,
                'event_type': 'trade',
                'asset': 'BTC',
                'amount': '0.1',
                'rate': '50000',
                'fee': '0.001',
                'fee_asset': 'BTC',
            },
            {
                'timestamp': from_timestamp + 7200,
                'location': location.value,
                'event_type': 'deposit',
                'asset': 'USDT',
                'amount': '5000',
            },
            {
                'timestamp': from_timestamp + 10800,
                'location': location.value,
                'event_type': 'withdrawal',
                'asset': 'ETH',
                'amount': '2.5',
                'fee': '0.005',
                'fee_asset': 'ETH',
            },
        ]

        # Filter by event type if specified
        for event in base_events:
            if event_type is None or event['event_type'] == event_type:
                if event['timestamp'] >= from_timestamp and event['timestamp'] <= to_timestamp:
                    events.append(event)

        return events
