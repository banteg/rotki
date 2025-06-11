"""Exchange manager implementation using ORM"""

import logging
from collections import defaultdict
from collections.abc import Iterator
from importlib import import_module
from typing import TYPE_CHECKING, Optional

from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.binance import BINANCE_BASE_URL, BINANCEUS_BASE_URL
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeApiCredentials,
    ExchangeAuthCredentials,
    Location,
)
from rotkehlchen.user_messages import MessagesAggregator

from .constants import EXCHANGES_WITHOUT_API_SECRET, SUPPORTED_EXCHANGES

if TYPE_CHECKING:
    from rotkehlchen.db.orm.database import RotkehlchenDatabase
    from rotkehlchen.exchanges.kraken import KrakenAccountType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ExchangeManager:
    """Exchange manager using ORM for database operations"""

    def __init__(self, msg_aggregator: MessagesAggregator, database: Optional['RotkehlchenDatabase'] = None) -> None:
        self.connected_exchanges: dict[Location, list[ExchangeInterface]] = defaultdict(list)
        self.msg_aggregator = msg_aggregator
        self.database = database

    def set_database(self, database: 'RotkehlchenDatabase') -> None:
        """Set the database instance"""
        self.database = database

    @staticmethod
    def _get_exchange_module_name(location: Location) -> str:
        if location == Location.BINANCEUS:
            return str(Location.BINANCE)

        return str(location)

    def connected_and_syncing_exchanges_num(self) -> int:
        return len(list(self.iterate_exchanges()))

    def get_exchange(self, name: str, location: Location) -> ExchangeInterface | None:
        """Get the exchange object for an exchange with a given name and location

        Returns None if it can not be found
        """
        exchanges_list = self.connected_exchanges.get(location)
        if exchanges_list is None:
            return None

        for exchange in exchanges_list:
            if exchange.name == name:
                return exchange

        return None

    def iterate_exchanges(self) -> Iterator[ExchangeInterface]:
        """Iterate all connected and syncing exchanges"""
        if not self.database:
            return

        # Get non-syncing exchanges from settings using ORM
        non_syncing_exchanges_str = self.database.repos.settings.get_setting('non_syncing_exchanges')
        excluded = set()
        if non_syncing_exchanges_str:
            # TODO: Parse the serialized list of excluded exchanges
            pass

        for exchanges in self.connected_exchanges.values():
            for exchange in exchanges:
                # We are not yielding excluded exchanges
                if exchange.location_id() not in excluded:
                    yield exchange

    def edit_exchange(
            self,
            name: str,
            location: Location,
            new_name: str | None,
            api_key: ApiKey | None,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: Optional['KrakenAccountType'],
            binance_selected_trade_pairs: list[str] | None,
    ) -> tuple[bool, str]:
        """Edits both the exchange object and the database entry using ORM

        Returns True if an entry was found and edited and false otherwise
        """
        exchangeobj = self.get_exchange(name=name, location=location)
        if not exchangeobj:
            return False, f'Could not find {location!s} exchange {name} for editing'

        # First validate exchange credentials
        edited = exchangeobj.edit_exchange_credentials(ExchangeAuthCredentials(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        ))
        if edited is True:
            try:
                credentials_are_valid, msg = exchangeobj.validate_api_key()
                if not credentials_are_valid:
                    exchangeobj.edit_exchange_credentials(
                        ExchangeAuthCredentials(
                            api_key=api_key,
                            api_secret=api_secret,
                            passphrase=passphrase,
                        ))
                    return False, msg
            except Exception as e:
                return False, str(e)

        # Update database using ORM
        if not self.database:
            return False, 'Database not initialized'

        with self.database.repos.unit_of_work():
            # Update credential
            updated = self.database.repos.credentials.update_credential(
                name=name,
                location=location,
                new_name=new_name,
                api_key=api_key.serialize() if api_key else None,
                api_secret=api_secret.serialize() if api_secret else None,
                passphrase=passphrase,
                kraken_account_type=kraken_account_type.serialize() if kraken_account_type else None,
            )

            if not updated:
                return False, f'Failed to update {location!s} exchange {name} in database'

            # TODO: Handle binance_selected_trade_pairs update
            # TODO: This might need a separate table or stored as JSON

        # Update the exchange object name if needed
        if new_name is not None:
            exchangeobj.name = new_name

        return True, ''

    def delete_exchange(self, name: str, location: Location) -> tuple[bool, str]:
        """Deletes an exchange from the manager and the database using ORM"""
        exchangeobj = self.get_exchange(name=name, location=location)
        if not exchangeobj:
            return False, f'Could not find {location!s} exchange {name} for deletion'

        # Remove from connected exchanges
        self.connected_exchanges[location].remove(exchangeobj)
        if len(self.connected_exchanges[location]) == 0:
            del self.connected_exchanges[location]

        # Delete from database using ORM
        if self.database:
            with self.database.repos.unit_of_work():
                success = self.database.repos.credentials.delete_credential(name, location)
                if not success:
                    log.warning(f'Failed to delete {location!s} exchange {name} from database')

        return True, ''

    def delete_all_exchanges(self) -> None:
        """Delete all exchanges from the manager"""
        self.connected_exchanges.clear()

    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: str | None = None,
            kraken_account_type: Optional['KrakenAccountType'] = None,
            binance_selected_trade_pairs: list[str] | None = None,
    ) -> tuple[bool, str]:
        """
        Setup a new exchange with given credentials and add to database using ORM
        """
        if location not in SUPPORTED_EXCHANGES:
            return False, f'Attempted to register unsupported exchange {location}'

        if self.get_exchange(name, location) is not None:
            return False, f'{location!s} exchange {name} already exists'

        # Save to database first using ORM
        if self.database:
            with self.database.repos.unit_of_work():
                try:
                    self.database.repos.credentials.add_credential(
                        name=name,
                        location=location.serialize_for_db(),
                        api_key=api_key.serialize(),
                        api_secret=api_secret.serialize() if api_secret else None,
                        passphrase=passphrase,
                        kraken_account_type=kraken_account_type.serialize() if kraken_account_type else None,
                    )

                    # TODO: Save binance_selected_trade_pairs if needed

                except Exception as e:
                    return False, f'Failed to save exchange to database: {e!s}'

        # Now initialize the exchange
        try:
            exchange = self._initialize_exchange(
                name=name,
                location=location,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                kraken_account_type=kraken_account_type,
                binance_selected_trade_pairs=binance_selected_trade_pairs,
            )
        except Exception as e:
            # Remove from database if initialization failed
            if self.database:
                with self.database.repos.unit_of_work():
                    self.database.repos.credentials.delete_credential(name, location)
            return False, str(e)

        self.connected_exchanges[location].append(exchange)
        return True, ''

    def _initialize_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: str | None = None,
            kraken_account_type: Optional['KrakenAccountType'] = None,
            binance_selected_trade_pairs: list[str] | None = None,
    ) -> ExchangeInterface:
        """Initialize an exchange object"""
        # Import the exchange module
        module_name = self._get_exchange_module_name(location)
        module = import_module(f'rotkehlchen.exchanges.{module_name}')

        # Get the exchange class
        exchange_class_name = location.name.capitalize()
        if location == Location.BINANCEUS:
            exchange_class_name = 'Binance'
        elif location == Location.CRYPTOCOM:
            exchange_class_name = 'Cryptocom'

        ExchangeClass = getattr(module, exchange_class_name)

        # Prepare initialization arguments
        init_args = {
            'name': name,
            'api_key': api_key,
            'secret': api_secret,
            'database': self.database,
            'msg_aggregator': self.msg_aggregator,
        }

        # Add exchange-specific arguments
        if location == Location.KRAKEN and kraken_account_type is not None:
            init_args['account_type'] = kraken_account_type

        if location in (Location.BINANCE, Location.BINANCEUS):
            if location == Location.BINANCEUS:
                init_args['base_uri'] = BINANCEUS_BASE_URL
            else:
                init_args['base_uri'] = BINANCE_BASE_URL

            if binance_selected_trade_pairs is not None:
                init_args['selected_trade_pairs'] = binance_selected_trade_pairs

        if passphrase is not None and location in EXCHANGES_WITHOUT_API_SECRET:
            init_args['passphrase'] = passphrase

        # Create and validate the exchange
        exchange = ExchangeClass(**init_args)

        # Validate API key
        success, msg = exchange.validate_api_key()
        if not success:
            raise InputError(f'Failed to validate {location} API key: {msg}')

        return exchange

    def initialize_exchanges(
            self,
            exchange_credentials: dict[Location, list[ExchangeApiCredentials]],
    ) -> None:
        """Initialize all exchanges from given credentials"""
        for location, credentials_list in exchange_credentials.items():
            for credentials in credentials_list:
                try:
                    exchange = self._initialize_exchange(
                        name=credentials.name,
                        location=location,
                        api_key=credentials.api_key,
                        api_secret=credentials.api_secret,
                        passphrase=credentials.passphrase,
                        kraken_account_type=credentials.kraken_account_type,
                        binance_selected_trade_pairs=credentials.binance_markets,
                    )
                    self.connected_exchanges[location].append(exchange)
                except Exception as e:
                    log.error(
                        f'Failed to initialize {location} exchange {credentials.name}: {e}',
                    )
                    self.msg_aggregator.add_error(
                        f'Failed to initialize {location} exchange {credentials.name}: {e}',
                    )
