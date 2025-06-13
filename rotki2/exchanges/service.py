"""High-level exchange service orchestrator.

This module provides the ExchangeService class that orchestrates
the client and mapper ports to provide a unified interface for
interacting with exchanges.
"""
import logging
from typing import TYPE_CHECKING, Any

from rotki2.exchanges.ports import (
    ExchangeApiClientPort,
    ExchangeDataMapperPort,
    ExchangeServicePort,
)
from rotki2.history.events.structures.asset import AssetMovement
from rotki2.history.events.structures.exchange import Trade
from rotki2.logging import RotkehlchenLogsAdapter
from rotki2.types import AssetAmount, Location, Timestamp

if TYPE_CHECKING:
    from rotki2.assets.base import Asset

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ExchangeService(ExchangeServicePort):
    """Generic exchange service that orchestrates client and mapper.
    
    This service implements the high-level exchange operations by
    delegating to the appropriate client and mapper implementations.
    It provides a clean interface for the core application to use.
    """
    
    def __init__(
        self,
        name: str,
        location: Location,
        client: ExchangeApiClientPort,
        mapper: ExchangeDataMapperPort,
    ) -> None:
        """Initialize the exchange service.
        
        Args:
            name: Exchange name for logging
            location: Exchange location identifier
            client: API client adapter instance
            mapper: Data mapper adapter instance
        """
        self.name = name
        self.location = location
        self.client = client
        self.mapper = mapper
        
    async def __aenter__(self) -> 'ExchangeService':
        """Async context manager entry."""
        if hasattr(self.client, '__aenter__'):
            await self.client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if hasattr(self.client, '__aexit__'):
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def query_balances(self) -> dict['Asset', AssetAmount]:
        """Query and return current balances.
        
        This method:
        1. Fetches raw balance data from the API client
        2. Transforms it using the data mapper
        3. Returns the normalized balance dictionary
        """
        log.debug(f'Querying {self.name} balances')
        
        try:
            # Fetch raw data from API
            raw_balances = await self.client.get_balances()
            
            # Transform to internal format
            balances = self.mapper.to_balances(raw_balances)
            
            log.debug(
                f'Retrieved {len(balances)} balances from {self.name}',
                asset_count=len(balances),
            )
            
            return balances
            
        except Exception as e:
            log.error(
                f'Failed to query {self.name} balances',
                error=str(e),
            )
            raise
    
    async def query_trades(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query and return trades within the time range.
        
        This method:
        1. Fetches raw trade data from the API client
        2. Transforms it using the data mapper
        3. Returns the list of Trade objects
        """
        log.debug(
            f'Querying {self.name} trades',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        
        try:
            # Fetch raw data from API
            raw_trades = await self.client.get_trades(start_ts, end_ts)
            
            # Transform to internal format
            trades = self.mapper.to_trades(raw_trades, self.location)
            
            log.debug(
                f'Retrieved {len(trades)} trades from {self.name}',
                trade_count=len(trades),
            )
            
            return trades
            
        except Exception as e:
            log.error(
                f'Failed to query {self.name} trades',
                error=str(e),
                start_ts=start_ts,
                end_ts=end_ts,
            )
            raise
    
    async def query_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query and return deposits/withdrawals within the time range.
        
        This method:
        1. Fetches raw deposit and withdrawal data from the API client
        2. Transforms both using the data mapper
        3. Returns the combined list of AssetMovement objects
        """
        log.debug(
            f'Querying {self.name} deposits and withdrawals',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        
        try:
            # Fetch raw data from API
            deposits, withdrawals = await self.client.get_deposits_withdrawals(
                start_ts,
                end_ts,
            )
            
            # Transform to internal format
            movements = self.mapper.to_asset_movements(
                deposits,
                withdrawals,
                self.location,
            )
            
            log.debug(
                f'Retrieved {len(movements)} asset movements from {self.name}',
                movement_count=len(movements),
                deposit_count=len(deposits),
                withdrawal_count=len(withdrawals),
            )
            
            return movements
            
        except Exception as e:
            log.error(
                f'Failed to query {self.name} deposits/withdrawals',
                error=str(e),
                start_ts=start_ts,
                end_ts=end_ts,
            )
            raise
    
    async def query_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> tuple[list[Trade], list[AssetMovement]]:
        """Query and return full history within the time range.
        
        This method queries both trades and asset movements in parallel
        for better performance.
        """
        log.debug(
            f'Querying {self.name} full history',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        
        # Query trades and movements concurrently
        import asyncio
        
        trades_task = asyncio.create_task(
            self.query_trades(start_ts, end_ts)
        )
        movements_task = asyncio.create_task(
            self.query_deposits_withdrawals(start_ts, end_ts)
        )
        
        trades, movements = await asyncio.gather(
            trades_task,
            movements_task,
            return_exceptions=False,
        )
        
        return trades, movements


class ExchangeServiceFactory:
    """Factory for creating exchange services with proper adapters.
    
    This factory simplifies the creation of exchange services by
    automatically instantiating the correct client and mapper adapters
    based on the exchange type.
    """
    
    # Registry of exchange adapters
    _adapters: dict[Location, tuple[type[ExchangeApiClientPort], type[ExchangeDataMapperPort]]] = {}
    
    @classmethod
    def register(
        cls,
        location: Location,
        client_class: type[ExchangeApiClientPort],
        mapper_class: type[ExchangeDataMapperPort],
    ) -> None:
        """Register adapter classes for an exchange.
        
        Args:
            location: Exchange location identifier
            client_class: API client adapter class
            mapper_class: Data mapper adapter class
        """
        cls._adapters[location] = (client_class, mapper_class)
    
    @classmethod
    def create(
        cls,
        location: Location,
        name: str,
        credentials: dict[str, Any],
    ) -> ExchangeService:
        """Create an exchange service with appropriate adapters.
        
        Args:
            location: Exchange location identifier
            name: Exchange name
            credentials: Authentication credentials
            
        Returns:
            Configured ExchangeService instance
            
        Raises:
            ValueError: If exchange is not registered
        """
        if location not in cls._adapters:
            raise ValueError(f'No adapters registered for {location.name}')
            
        client_class, mapper_class = cls._adapters[location]
        
        # Instantiate adapters
        client = client_class(**credentials)
        mapper = mapper_class()
        
        # Create service
        return ExchangeService(
            name=name,
            location=location,
            client=client,
            mapper=mapper,
        )


# Register exchange adapters
from rotki2.exchanges.adapters.okx.client import OkxApiClient
from rotki2.exchanges.adapters.okx.mapper import OkxDataMapper
from rotki2.exchanges.adapters.kraken.client import KrakenApiClient
from rotki2.exchanges.adapters.kraken.mapper import KrakenDataMapper
from rotki2.exchanges.adapters.binance.client import BinanceApiClient
from rotki2.exchanges.adapters.binance.mapper import BinanceDataMapper
from rotki2.exchanges.adapters.coinbase.client import CoinbaseApiClient
from rotki2.exchanges.adapters.coinbase.mapper import CoinbaseDataMapper

# Register all exchange adapters
ExchangeServiceFactory.register(Location.OKX, OkxApiClient, OkxDataMapper)
ExchangeServiceFactory.register(Location.KRAKEN, KrakenApiClient, KrakenDataMapper)
ExchangeServiceFactory.register(Location.BINANCE, BinanceApiClient, BinanceDataMapper)
ExchangeServiceFactory.register(Location.BINANCEUS, BinanceApiClient, BinanceDataMapper)
ExchangeServiceFactory.register(Location.COINBASE, CoinbaseApiClient, CoinbaseDataMapper)