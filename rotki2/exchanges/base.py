"""Async base classes for exchange implementations"""
import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import anyio

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    MarginPosition,
    Trade,
)
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotki2.utils.async_http_client import AsyncHTTPClient

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = RotkehlchenLogsAdapter(__name__)


class AsyncExchangeInterface(ABC):
    """Async base interface for exchanges
    
    This is the async version of ExchangeInterface, converting all I/O operations
    to async while maintaining the same functionality.
    """
    
    def __init__(
        self,
        name: str,
        location: Location,
        api_key: ApiKey,
        secret: ApiSecret,
        database: 'DBHandler',
        msg_aggregator: MessagesAggregator,
        http_client: AsyncHTTPClient | None = None,
    ):
        self.name = name
        self.location = location
        self.api_key = api_key
        self.secret = secret
        self.db = database
        self.msg_aggregator = msg_aggregator
        self.http_client = http_client or AsyncHTTPClient()
        
        # Rate limiting
        self.first_connection_made = False
        self.call_counter = 0
        self.last_query_ts = 0
        self._rate_limit_lock = asyncio.Lock()
        
    @abstractmethod
    async def query_balances(self, **kwargs: Any) -> dict[Asset, Balance]:
        """Query account balances
        
        Returns a dict of Asset -> Balance
        """
        
    @abstractmethod
    async def query_online_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history within the given time range"""
        
    @abstractmethod
    async def query_online_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals within the given time range"""
    
    @abstractmethod
    async def validate_api_key(self) -> tuple[bool, str]:
        """Validate that the API key is correct
        
        Returns (success, error_message)
        """
    
    async def first_connection(self) -> None:
        """Perform first connection initialization
        
        Called the first time an exchange is connected to.
        Can be overridden by subclasses for exchange-specific initialization.
        """
        if self.first_connection_made:
            return
            
        self.first_connection_made = True
        # Validate API key on first connection
        success, msg = await self.validate_api_key()
        if not success:
            raise RemoteError(f'Failed to validate {self.name} API key: {msg}')
    
    async def query_online_margin_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[MarginPosition]:
        """Query margin positions history
        
        Default implementation returns empty list.
        Override in exchanges that support margin trading.
        """
        return []
    
    async def query_exchange_specific_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> Any:
        """Query exchange-specific history data
        
        Override in exchanges that have unique data types.
        """
        return None
    
    async def close(self) -> None:
        """Close exchange connections and cleanup"""
        if self.http_client:
            await self.http_client.close()
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting before making API calls
        
        Should be called before each API request.
        Can be overridden for exchange-specific rate limiting.
        """
        async with self._rate_limit_lock:
            # Simple rate limiting - ensure minimum time between calls
            now = ts_now()
            time_since_last = now - self.last_query_ts
            
            # Default to 1 request per second
            min_interval = 1.0
            if time_since_last < min_interval:
                await anyio.sleep(min_interval - time_since_last)
            
            self.last_query_ts = ts_now()
            self.call_counter += 1


class AsyncExchangeWithExtras(AsyncExchangeInterface):
    """Base class for exchanges that have extra configuration
    
    Such as Kraken with account types or Binance with selected markets.
    """
    
    @abstractmethod
    def get_extras(self) -> dict[str, Any]:
        """Get exchange-specific extra configuration"""
        
    @abstractmethod
    def set_extras(self, extras: dict[str, Any]) -> None:
        """Set exchange-specific extra configuration"""
        

class AsyncExchangeWithoutApiSecret(ABC):
    """Base class for exchanges that don't require an API secret
    
    Some exchanges like some DEXes only need an address, not API credentials.
    """
    
    def __init__(
        self,
        name: str,
        location: Location,
        database: 'DBHandler',
        msg_aggregator: MessagesAggregator,
        http_client: AsyncHTTPClient | None = None,
    ):
        self.name = name
        self.location = location
        self.db = database
        self.msg_aggregator = msg_aggregator
        self.http_client = http_client or AsyncHTTPClient()
    
    @abstractmethod
    async def query_balances(self, **kwargs: Any) -> dict[Asset, Balance]:
        """Query account balances"""
        
    async def close(self) -> None:
        """Close connections and cleanup"""
        if self.http_client:
            await self.http_client.close()