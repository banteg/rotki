"""Async price historian for historical price queries"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.price import (
    NoPriceForGivenTimestamp,
    PriceQueryUnsupportedAsset,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import HistoricalPriceOracle, Price, Timestamp
from rotki2.externalapis.coingecko import AsyncCoingecko
from rotki2.externalapis.cryptocompare import AsyncCryptocompare
from rotki2.externalapis.defillama import AsyncDefillama

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = RotkehlchenLogsAdapter(__name__)


class AsyncPriceHistorian:
    """Async version of PriceHistorian for querying historical prices
    
    This class manages historical price lookups using async oracles.
    """
    
    def __init__(
        self,
        cryptocompare: AsyncCryptocompare | None = None,
        coingecko: AsyncCoingecko | None = None,
        defillama: AsyncDefillama | None = None,
    ):
        # Initialize oracles
        self.cryptocompare = cryptocompare or AsyncCryptocompare()
        self.coingecko = coingecko or AsyncCoingecko()
        self.defillama = defillama or AsyncDefillama()
        
        # Oracle configuration
        self._oracles: list[HistoricalPriceOracle] = []
        self._oracle_instances: dict[HistoricalPriceOracle, Any] = {}
        
        # Set default oracle order
        self.set_oracles_order([
            HistoricalPriceOracle.DEFILLAMA,
            HistoricalPriceOracle.CRYPTOCOMPARE,
            HistoricalPriceOracle.COINGECKO,
            HistoricalPriceOracle.MANUAL,
        ])
        
        # Price cache - could implement LRU cache here
        self._price_cache: dict[tuple[Asset, Asset, Timestamp], Price] = {}
    
    def set_oracles_order(self, oracles: Sequence[HistoricalPriceOracle]) -> None:
        """Set the order of oracles to query for historical prices"""
        self._oracles = list(oracles)
        
        # Map oracle types to instances
        self._oracle_instances = {
            HistoricalPriceOracle.CRYPTOCOMPARE: self.cryptocompare,
            HistoricalPriceOracle.COINGECKO: self.coingecko,
            HistoricalPriceOracle.DEFILLAMA: self.defillama,
        }
    
    async def query_historical_price(
        self,
        from_asset: Asset,
        to_asset: Asset,
        timestamp: Timestamp,
    ) -> Price:
        """Query historical price at a specific timestamp
        
        Tries each configured oracle in order until a price is found.
        """
        # Check cache first
        cache_key = (from_asset, to_asset, timestamp)
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        # Try each oracle
        for oracle_type in self._oracles:
            if oracle_type not in self._oracle_instances:
                continue
                
            oracle = self._oracle_instances[oracle_type]
            
            try:
                price = await self._query_oracle_historical_price(
                    oracle=oracle,
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
                
                if price != ZERO_PRICE:
                    # Cache the result
                    self._price_cache[cache_key] = price
                    return price
                    
            except (PriceQueryUnsupportedAsset, Exception) as e:
                logger.debug(
                    f'Oracle {oracle_type} failed to get historical price for '
                    f'{from_asset.identifier} to {to_asset.identifier} '
                    f'at {timestamp}: {e}'
                )
                continue
        
        # No oracle could provide the price
        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
    
    async def _query_oracle_historical_price(
        self,
        oracle: Any,
        from_asset: Asset,
        to_asset: Asset,
        timestamp: Timestamp,
    ) -> Price:
        """Query a specific oracle for historical price"""
        # Each oracle has async query_historical_price method
        if hasattr(oracle, 'query_historical_price'):
            return await oracle.query_historical_price(
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )
        
        return ZERO_PRICE
    
    async def get_historical_price_range(
        self,
        from_asset: Asset,
        to_asset: Asset,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> list[tuple[Timestamp, Price]]:
        """Get historical prices for a time range
        
        Returns list of (timestamp, price) tuples.
        """
        prices = []
        
        # For now, query daily prices
        # In a full implementation, this would be optimized
        current_ts = from_timestamp
        day_seconds = 86400
        
        while current_ts <= to_timestamp:
            try:
                price = await self.query_historical_price(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=current_ts,
                )
                prices.append((current_ts, price))
            except NoPriceForGivenTimestamp:
                # Skip missing prices
                pass
            
            current_ts = Timestamp(current_ts + day_seconds)
        
        return prices
    
    def get_oracles(self) -> list[HistoricalPriceOracle]:
        """Get the configured oracle order"""
        return self._oracles.copy()
    
    async def close(self) -> None:
        """Close all oracle connections"""
        if self.cryptocompare:
            await self.cryptocompare.close()
        if self.coingecko:
            await self.coingecko.close()
        if self.defillama:
            await self.defillama.close()