"""Exchange manager v2 - integrates with the new Ports & Adapters architecture.

This manager handles multiple exchange connections using the new service-based
architecture while maintaining backward compatibility.
"""
import logging
from typing import TYPE_CHECKING, Any

from rotki2.assets.base import Asset
from rotki2.constants.assets import A_USD
from rotki2.errors.misc import InputError, RemoteError
from rotki2.exchanges.ports import ExchangeServicePort
from rotki2.exchanges.service import ExchangeService, ExchangeServiceFactory
from rotki2.history.events.structures.asset import AssetMovement
from rotki2.history.events.structures.exchange import Trade
from rotki2.logging import RotkehlchenLogsAdapter
from rotki2.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    Location,
    Timestamp,
)
from rotki2.utils.misc import combine_asset_dicts

if TYPE_CHECKING:
    from rotki2.db.dbhandler import DBHandler
    from rotki2.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Legacy exchange classes for backward compatibility
from rotki2.exchanges.base import ExchangeInterface
from rotki2.exchanges.binance import Binance
from rotki2.exchanges.bitfinex import Bitfinex
from rotki2.exchanges.bitstamp import Bitstamp
from rotki2.exchanges.coinbase import Coinbase
from rotki2.exchanges.kraken import Kraken
from rotki2.exchanges.okx import OKX

# Map of supported exchanges (legacy)
LEGACY_EXCHANGE_MAPPING = {
    Location.BINANCE: Binance,
    Location.BINANCEUS: Binance,
    Location.BITFINEX: Bitfinex,
    Location.BITSTAMP: Bitstamp,
    Location.COINBASE: Coinbase,
    Location.KRAKEN: Kraken,
    Location.OKX: OKX,
}

# Exchanges that have been migrated to the new architecture
MIGRATED_EXCHANGES = {
    Location.OKX,
    Location.KRAKEN,
    Location.BINANCE,
    Location.BINANCEUS,
    Location.COINBASE,
}


class ExchangeManagerV2:
    """Exchange manager that supports both legacy and new architectures.
    
    This manager provides a migration path from the monolithic exchange
    classes to the new Ports & Adapters architecture. It can handle both
    types of exchanges transparently.
    """
    
    def __init__(
        self,
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
    ) -> None:
        """Initialize the exchange manager."""
        self.db = database
        self.msg_aggregator = msg_aggregator
        
        # Legacy exchanges (will be phased out)
        self.legacy_exchanges: dict[Location, list[ExchangeInterface]] = {}
        
        # New service-based exchanges
        self.service_exchanges: dict[Location, list[ExchangeService]] = {}
        
        # Unified view for iteration
        self._all_exchanges: dict[str, ExchangeServicePort | ExchangeInterface] = {}
    
    def _use_new_architecture(self, location: Location) -> bool:
        """Check if an exchange should use the new architecture."""
        return location in MIGRATED_EXCHANGES
    
    async def setup_exchange(
        self,
        name: str,
        location: Location,
        api_key: ApiKey,
        api_secret: ApiSecret | None,
        passphrase: str | None = None,
        **kwargs: Any,
    ) -> tuple[bool, str]:
        """Setup a new exchange connection.
        
        This method determines whether to use the legacy or new architecture
        based on the exchange location.
        """
        # Check if exchange already exists
        if name in self._all_exchanges:
            return False, f'Exchange {name} already exists'
            
        # Check if exchange is supported
        if location not in LEGACY_EXCHANGE_MAPPING:
            return False, f'Exchange {location} is not supported yet'
        
        try:
            if self._use_new_architecture(location):
                # Use new service-based architecture
                success, msg = await self._setup_service_exchange(
                    name, location, api_key, api_secret, passphrase, **kwargs
                )
            else:
                # Use legacy architecture
                success, msg = await self._setup_legacy_exchange(
                    name, location, api_key, api_secret, passphrase, **kwargs
                )
                
            return success, msg
            
        except Exception as e:
            log.error(
                f'Unexpected error setting up {location} exchange',
                error=str(e),
                location=location,
                name=name,
            )
            return False, f'Failed to setup exchange: {str(e)}'
    
    async def _setup_service_exchange(
        self,
        name: str,
        location: Location,
        api_key: ApiKey,
        api_secret: ApiSecret | None,
        passphrase: str | None = None,
        **kwargs: Any,
    ) -> tuple[bool, str]:
        """Setup an exchange using the new service architecture."""
        log.info(f'Setting up {location} exchange using new architecture', name=name)
        
        # Build credentials dictionary
        credentials = {
            'api_key': api_key,
            'secret': api_secret,
        }
        
        # Add exchange-specific credentials
        if location in (Location.KUCOIN, Location.OKX, Location.COINBASEPRIME):
            if passphrase:
                credentials['passphrase'] = passphrase
                
        try:
            # Create service using factory
            service = ExchangeServiceFactory.create(
                location=location,
                name=name,
                credentials=credentials,
            )
            
            # Initialize the service (opens HTTP client)
            await service.__aenter__()
            
            # Validate by querying balances
            try:
                await service.query_balances()
            except Exception as e:
                await service.__aexit__(None, None, None)
                return False, f'Invalid API credentials: {str(e)}'
                
            # Add to service exchanges
            if location not in self.service_exchanges:
                self.service_exchanges[location] = []
            self.service_exchanges[location].append(service)
            
            # Add to unified view
            self._all_exchanges[name] = service
            
            return True, ''
            
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            log.error(
                f'Failed to create {location} service',
                error=str(e),
                location=location,
            )
            return False, f'Failed to setup exchange: {str(e)}'
    
    async def _setup_legacy_exchange(
        self,
        name: str,
        location: Location,
        api_key: ApiKey,
        api_secret: ApiSecret | None,
        passphrase: str | None = None,
        **kwargs: Any,
    ) -> tuple[bool, str]:
        """Setup an exchange using the legacy architecture."""
        log.info(f'Setting up {location} exchange using legacy architecture', name=name)
        
        exchange_class = LEGACY_EXCHANGE_MAPPING[location]
        
        # Build exchange-specific kwargs
        exchange_kwargs = {
            'name': name,
            'api_key': api_key,
            'secret': api_secret,
            'database': self.db,
            'msg_aggregator': self.msg_aggregator,
        }
        
        # Add exchange-specific parameters
        if location == Location.KRAKEN and 'kraken_account_type' in kwargs:
            exchange_kwargs['kraken_account_type'] = kwargs['kraken_account_type']
        elif location in (Location.BINANCE, Location.BINANCEUS):
            if 'binance_markets' in kwargs:
                exchange_kwargs['binance_markets'] = kwargs['binance_markets']
            if location == Location.BINANCEUS:
                from rotki2.exchanges.binance import BINANCEUS_BASE_URL
                exchange_kwargs['uri'] = BINANCEUS_BASE_URL
        elif location in (Location.KUCOIN, Location.OKX, Location.COINBASEPRIME):
            if passphrase:
                exchange_kwargs['passphrase'] = passphrase
                
        # Create instance
        exchange = exchange_class(**exchange_kwargs)
        
        # Validate credentials
        await exchange.first_connection()
        
        # Add to legacy exchanges
        if location not in self.legacy_exchanges:
            self.legacy_exchanges[location] = []
        self.legacy_exchanges[location].append(exchange)
        
        # Add to unified view
        self._all_exchanges[name] = exchange
        
        return True, ''
    
    async def delete_exchange(
        self,
        name: str,
        location: Location | None = None,
    ) -> tuple[bool, str]:
        """Remove an exchange connection."""
        if name not in self._all_exchanges:
            return False, f'Exchange {name} not found'
            
        exchange = self._all_exchanges[name]
        
        # Determine location if not provided
        if location is None:
            if isinstance(exchange, ExchangeService):
                location = exchange.location
            else:
                location = exchange.location
                
        # Remove from appropriate list
        if self._use_new_architecture(location) and location in self.service_exchanges:
            for i, service in enumerate(self.service_exchanges[location]):
                if service.name == name:
                    # Close the service
                    await service.__aexit__(None, None, None)
                    self.service_exchanges[location].pop(i)
                    if not self.service_exchanges[location]:
                        del self.service_exchanges[location]
                    break
        elif location in self.legacy_exchanges:
            for i, legacy in enumerate(self.legacy_exchanges[location]):
                if legacy.name == name:
                    # Close the exchange
                    await legacy.close()
                    self.legacy_exchanges[location].pop(i)
                    if not self.legacy_exchanges[location]:
                        del self.legacy_exchanges[location]
                    break
                    
        # Remove from unified view
        del self._all_exchanges[name]
        
        return True, ''
    
    def get_exchange(self, name: str) -> ExchangeServicePort | ExchangeInterface | None:
        """Get a specific exchange instance by name."""
        return self._all_exchanges.get(name)
    
    def iterate_exchanges(self) -> list[ExchangeServicePort | ExchangeInterface]:
        """Iterate through all connected exchanges."""
        return list(self._all_exchanges.values())
    
    async def query_all_balances(
        self,
        ignore_cache: bool = False,
    ) -> tuple[dict[Location, dict[Asset, AssetAmount]], list[str]]:
        """Query balances from all connected exchanges.
        
        Returns (balances_by_location, errors)
        """
        all_balances: dict[Location, dict[Asset, AssetAmount]] = {}
        errors = []
        
        for name, exchange in self._all_exchanges.items():
            try:
                if isinstance(exchange, ExchangeService):
                    # New architecture
                    balances = await exchange.query_balances()
                    location = exchange.location
                else:
                    # Legacy architecture
                    raw_balances = await exchange.query_balances(ignore_cache=ignore_cache)
                    # Convert Balance objects to AssetAmount
                    balances = {
                        asset: balance.amount
                        for asset, balance in raw_balances.items()
                    }
                    location = exchange.location
                    
                # Combine with existing balances for this location
                if location in all_balances:
                    all_balances[location] = combine_asset_dicts(
                        all_balances[location],
                        balances,
                    )
                else:
                    all_balances[location] = balances
                    
            except Exception as e:
                error_msg = f'Failed to query {name} balances: {str(e)}'
                errors.append(error_msg)
                log.error(error_msg, error=str(e), exchange=name)
                
        return all_balances, errors
    
    async def query_exchange_history(
        self,
        name: str,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> tuple[list[Trade], list[AssetMovement], list[str]]:
        """Query history from a specific exchange.
        
        Returns (trades, movements, errors)
        """
        exchange = self._all_exchanges.get(name)
        if not exchange:
            return [], [], [f'Exchange {name} not found']
            
        errors = []
        trades: list[Trade] = []
        movements: list[AssetMovement] = []
        
        try:
            if isinstance(exchange, ExchangeService):
                # New architecture returns proper types
                trades, movements = await exchange.query_history(start_ts, end_ts)
            else:
                # Legacy architecture
                legacy_trades = await exchange.query_online_trade_history(
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
                legacy_movements = await exchange.query_online_deposits_withdrawals(
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
                
                # Convert legacy types to new types if needed
                # (This assumes legacy exchanges return the same types for now)
                trades = legacy_trades
                movements = legacy_movements
                
        except Exception as e:
            error_msg = f'Failed to query {name} history: {str(e)}'
            errors.append(error_msg)
            log.error(error_msg, error=str(e), exchange=name)
            
        return trades, movements, errors
    
    async def close_all(self) -> None:
        """Close all exchange connections."""
        # Close service exchanges
        for services in self.service_exchanges.values():
            for service in services:
                try:
                    await service.__aexit__(None, None, None)
                except Exception as e:
                    log.error(
                        f'Error closing service {service.name}',
                        error=str(e),
                    )
                    
        # Close legacy exchanges
        for exchanges in self.legacy_exchanges.values():
            for exchange in exchanges:
                try:
                    await exchange.close()
                except Exception as e:
                    log.error(
                        f'Error closing exchange {exchange.name}',
                        error=str(e),
                    )
                    
        # Clear all collections
        self.service_exchanges.clear()
        self.legacy_exchanges.clear()
        self._all_exchanges.clear()