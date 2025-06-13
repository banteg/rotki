"""Async exchange manager for handling multiple exchange connections"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    MarginPosition,
    Trade,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    Location,
    Timestamp,
)
from rotkehlchen.utils.misc import combine_dicts
from rotki2.exchanges.base import ExchangeInterface
from rotki2.exchanges.kraken import Kraken

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = RotkehlchenLogsAdapter(__name__)

# Map of supported exchanges
EXCHANGE_MAPPING = {
    Location.KRAKEN: Kraken,
    # Add more exchanges as they are implemented
    # Location.BINANCE: Binance,
    # Location.COINBASE: Coinbase,
}


class ExchangeManager:
    """Manager for exchange instances
    
    Handles multiple exchange connections and provides unified interfaces.
    All operations are async.
    """
    
    def __init__(
        self,
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
    ):
        self.db = database
        self.msg_aggregator = msg_aggregator
        self.connected_exchanges: dict[Location, list[ExchangeInterface]] = {}
        
    async def setup_exchange(
        self,
        name: str,
        location: Location,
        api_key: ApiKey,
        api_secret: ApiSecret | None,
        database: 'DBHandler',
        passphrase: str | None = None,
        **kwargs: Any,
    ) -> tuple[bool, str]:
        """Setup a new exchange connection
        
        Returns (success, message)
        """
        if location not in EXCHANGE_MAPPING:
            return False, f'Exchange {location} is not supported yet'
        
        # Check if exchange with same name already exists
        if location in self.connected_exchanges:
            for exchange in self.connected_exchanges[location]:
                if exchange.name == name:
                    return False, f'Exchange {name} already exists'
        
        # Create exchange instance
        exchange_class = EXCHANGE_MAPPING[location]
        
        try:
            # Build exchange-specific kwargs
            exchange_kwargs = {
                'name': name,
                'api_key': api_key,
                'secret': api_secret,
                'database': database,
                'msg_aggregator': self.msg_aggregator,
            }
            
            # Add exchange-specific parameters
            if location == Location.KRAKEN and 'kraken_account_type' in kwargs:
                exchange_kwargs['kraken_account_type'] = kwargs['kraken_account_type']
            
            # Create instance
            exchange = exchange_class(**exchange_kwargs)
            
            # Validate credentials
            await exchange.first_connection()
            
            # Add to connected exchanges
            if location not in self.connected_exchanges:
                self.connected_exchanges[location] = []
            self.connected_exchanges[location].append(exchange)
            
            return True, ''
            
        except RemoteError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f'Unexpected error setting up {location} exchange: {e}')
            return False, f'Failed to setup exchange: {str(e)}'
    
    async def delete_exchange(
        self,
        name: str,
        location: Location,
    ) -> tuple[bool, str]:
        """Remove an exchange connection
        
        Returns (success, message)
        """
        if location not in self.connected_exchanges:
            return False, f'No {location} exchange connected'
        
        exchanges = self.connected_exchanges[location]
        for i, exchange in enumerate(exchanges):
            if exchange.name == name:
                # Close the exchange connection
                await exchange.close()
                
                # Remove from list
                exchanges.pop(i)
                
                # Clean up empty location
                if not exchanges:
                    del self.connected_exchanges[location]
                
                return True, ''
        
        return False, f'Exchange {name} not found'
    
    async def edit_exchange(
        self,
        name: str,
        location: Location,
        new_name: str | None = None,
        api_key: ApiKey | None = None,
        api_secret: ApiSecret | None = None,
        passphrase: str | None = None,
        database: 'DBHandler' | None = None,
        **kwargs: Any,
    ) -> tuple[bool, str]:
        """Edit an existing exchange connection
        
        Returns (success, message)
        """
        if location not in self.connected_exchanges:
            return False, f'No {location} exchange connected'
        
        exchange = None
        for ex in self.connected_exchanges[location]:
            if ex.name == name:
                exchange = ex
                break
        
        if not exchange:
            return False, f'Exchange {name} not found'
        
        # If credentials changed, validate them
        if api_key or api_secret:
            # Save old credentials
            old_key = exchange.api_key
            old_secret = exchange.secret
            
            # Update credentials
            if api_key:
                exchange.api_key = api_key
            if api_secret:
                exchange.secret = api_secret
            
            # Validate new credentials
            try:
                success, msg = await exchange.validate_api_key()
                if not success:
                    # Restore old credentials
                    exchange.api_key = old_key
                    exchange.secret = old_secret
                    return False, msg
            except Exception as e:
                # Restore old credentials
                exchange.api_key = old_key
                exchange.secret = old_secret
                return False, str(e)
        
        # Update name if provided
        if new_name:
            exchange.name = new_name
        
        # Update exchange-specific extras
        if hasattr(exchange, 'set_extras') and kwargs:
            exchange.set_extras(kwargs)
        
        return True, ''
    
    def get_exchange(self, name: str, location: Location) -> ExchangeInterface | None:
        """Get a specific exchange instance"""
        if location not in self.connected_exchanges:
            return None
            
        for exchange in self.connected_exchanges[location]:
            if exchange.name == name:
                return exchange
        
        return None
    
    def iterate_exchanges(self) -> list[ExchangeInterface]:
        """Iterate through all connected exchanges"""
        exchanges = []
        for location_exchanges in self.connected_exchanges.values():
            exchanges.extend(location_exchanges)
        return exchanges
    
    async def query_all_balances(
        self,
        ignore_cache: bool = False,
    ) -> tuple[dict[Location, dict[Asset, Balance]], list[str]]:
        """Query balances from all connected exchanges
        
        Returns (balances_by_location, errors)
        """
        all_balances = {}
        errors = []
        
        for exchange in self.iterate_exchanges():
            try:
                balances = await exchange.query_balances(ignore_cache=ignore_cache)
                
                # Combine with existing balances for this location
                if exchange.location in all_balances:
                    all_balances[exchange.location] = combine_dicts(
                        all_balances[exchange.location],
                        balances,
                    )
                else:
                    all_balances[exchange.location] = balances
                    
            except Exception as e:
                error_msg = f'Failed to query {exchange.name} balances: {str(e)}'
                errors.append(error_msg)
                logger.error(error_msg)
        
        return all_balances, errors
    
    async def query_exchange_balances(
        self,
        location: Location,
        ignore_cache: bool = False,
    ) -> tuple[dict[Asset, Balance], list[str]]:
        """Query balances from specific exchange type
        
        Returns (combined_balances, errors)
        """
        if location not in self.connected_exchanges:
            return {}, [f'No {location} exchange connected']
        
        combined_balances = {}
        errors = []
        
        for exchange in self.connected_exchanges[location]:
            try:
                balances = await exchange.query_balances(ignore_cache=ignore_cache)
                combined_balances = combine_dicts(combined_balances, balances)
            except Exception as e:
                error_msg = f'Failed to query {exchange.name} balances: {str(e)}'
                errors.append(error_msg)
                logger.error(error_msg)
        
        return combined_balances, errors
    
    async def close_all(self) -> None:
        """Close all exchange connections"""
        for exchanges in self.connected_exchanges.values():
            for exchange in exchanges:
                await exchange.close()
        
        self.connected_exchanges.clear()