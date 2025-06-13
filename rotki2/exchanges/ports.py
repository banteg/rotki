"""Exchange ports - abstract interfaces for the hexagonal architecture.

These interfaces define the contracts that exchange implementations must follow.
They are the boundary between the core application logic and external exchange APIs.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from rotki2.assets.base import Asset
from rotki2.assets.types import EvmTokenKind
from rotki2.db.settings import CachedSettings
from rotki2.history.events.structures.asset import AssetMovement
from rotki2.history.events.structures.eth2 import EthWithdrawalEvent
from rotki2.history.events.structures.exchange import Trade
from rotki2.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotki2.serialization.deserialize import deserialize_timestamp_from_floatstr
from rotki2.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)
from rotki2.utils.misc import ts_sec_to_ms


class ExchangeApiClientPort(ABC):
    """Port for exchange API client adapters.
    
    This interface defines methods for fetching raw data from exchange APIs.
    Implementations should handle authentication, rate limiting, and pagination.
    Returns raw data (typically lists of dictionaries) without transformation.
    """
    
    @abstractmethod
    async def get_balances(self) -> list[dict[str, Any]]:
        """Fetch current balances from the exchange."""
        ...
    
    @abstractmethod
    async def get_trades(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch trades within the given time range."""
        ...
    
    @abstractmethod
    async def get_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch deposits and withdrawals within the given time range."""
        ...
    
    @abstractmethod
    async def get_order_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch order history within the given time range."""
        ...
    
    @abstractmethod
    async def get_markets(self) -> list[dict[str, Any]]:
        """Fetch available trading markets/pairs."""
        ...


class ExchangeDataMapperPort(ABC):
    """Port for exchange data mapper adapters.
    
    This interface defines methods for transforming raw exchange data
    into Rotki's internal domain models. Implementations should handle
    asset mapping, error cases, and data validation.
    """
    
    @abstractmethod
    def to_balances(self, raw_data: list[dict[str, Any]]) -> dict[Asset, AssetAmount]:
        """Transform raw balance data into Rotki balance format."""
        ...
    
    @abstractmethod
    def to_trades(
        self,
        raw_data: list[dict[str, Any]],
        location: Location,
    ) -> list[Trade]:
        """Transform raw trade data into Rotki Trade objects."""
        ...
    
    @abstractmethod
    def to_asset_movements(
        self,
        deposits: list[dict[str, Any]],
        withdrawals: list[dict[str, Any]],
        location: Location,
    ) -> list[AssetMovement]:
        """Transform raw deposit/withdrawal data into AssetMovement objects."""
        ...
    
    @abstractmethod
    def map_asset(self, exchange_symbol: str) -> Asset | None:
        """Map exchange-specific asset symbol to Rotki Asset.
        
        Returns None if the asset cannot be mapped.
        """
        ...


class ExchangeServicePort(ABC):
    """Port for the high-level exchange service.
    
    This interface defines the public API that the core application uses
    to interact with exchanges. It orchestrates the client and mapper ports.
    """
    
    @abstractmethod
    async def query_balances(self) -> dict[Asset, AssetAmount]:
        """Query and return current balances."""
        ...
    
    @abstractmethod
    async def query_trades(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query and return trades within the time range."""
        ...
    
    @abstractmethod
    async def query_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query and return deposits/withdrawals within the time range."""
        ...
    
    @abstractmethod
    async def query_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> tuple[list[Trade], list[AssetMovement]]:
        """Query and return full history (trades + movements) within the time range."""
        ...


class ExchangeAuthPort(ABC):
    """Port for exchange authentication mechanisms.
    
    This interface defines methods for handling exchange-specific authentication.
    """
    
    @abstractmethod
    def sign_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Sign a request and return authentication headers."""
        ...
    
    @abstractmethod
    def get_nonce(self) -> str:
        """Generate a nonce for the request if required."""
        ...