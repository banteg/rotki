"""Async Inquirer service for price queries and external data fetching"""
import asyncio
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import AssetWithNameAndType, AssetWithOracles, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.prices import CURRENT_PRICE_CACHE_SECS
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.price import (
    NoPriceError,
    PriceQueryUnsupportedAsset,
    RemoteError,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    CurrentPriceOracle,
    EvmTokenKind,
    HistoricalPriceOracle,
    Price,
    Timestamp,
)
from rotkehlchen.utils.misc import set_user_agent, ts_now
from rotki2.utils.async_network import AsyncHTTPClient

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.assets.asset import Asset, CryptoAsset, FiatAsset
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.externalapis.alchemy import Alchemy
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.externalapis.defillama import Defillama
    from rotkehlchen.externalapis.manualcurrent import ManualCurrentOracle
    from rotkehlchen.types import PriceOracleInstance

logger = RotkehlchenLogsAdapter(__name__)


class CachedPriceEntry:
    """Represents a cached price entry"""
    def __init__(self, price: Price, time: Timestamp):
        self.price = price
        self.time = time
        
    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        return ts_now() - self.time >= CURRENT_PRICE_CACHE_SECS


class AsyncInquirer:
    """Async version of the Inquirer for price queries and external data
    
    This service migrates the price inquiry logic from the synchronous
    Inquirer to an async-first architecture.
    """

    def __init__(
        self,
        cryptocompare: 'Cryptocompare',
        coingecko: 'Coingecko', 
        defillama: 'Defillama',
        alchemy: 'Alchemy',
        manualcurrent: 'ManualCurrentOracle',
        http_client: AsyncHTTPClient | None = None,
    ):
        self.cryptocompare = cryptocompare
        self.coingecko = coingecko
        self.defillama = defillama
        self.alchemy = alchemy
        self.manualcurrent = manualcurrent
        self.http_client = http_client or AsyncHTTPClient()
        
        # Price cache - using async lock for thread safety
        self._cached_current_price: dict[tuple[AssetWithOracles, Asset], CachedPriceEntry] = {}
        self._cache_lock = asyncio.Lock()
        
        # EVM managers registry
        self._evm_managers: dict[ChainID, 'EvmNodeInquirer'] = {}
        
        # Oracle configuration
        self._oracles: list[CurrentPriceOracle] = []
        self._oracle_instances: list['PriceOracleInstance'] = []
        self._defi_oracles: list['PriceOracleInstance'] = []
        
        # Set default oracle order
        self.set_oracles_order([
            CurrentPriceOracle.DEFILLAMA,
            CurrentPriceOracle.CRYPTOCOMPARE,
            CurrentPriceOracle.COINGECKO,
            CurrentPriceOracle.UNISWAPV2,
            CurrentPriceOracle.UNISWAPV3,
            CurrentPriceOracle.MANUALCURRENT,
        ])

    def set_oracles_order(self, oracles: Sequence[CurrentPriceOracle]) -> None:
        """Set the order of oracles to query for prices"""
        self._oracles = list(oracles)
        
        # Map oracle types to instances
        instances_map = {
            CurrentPriceOracle.CRYPTOCOMPARE: self.cryptocompare,
            CurrentPriceOracle.COINGECKO: self.coingecko,
            CurrentPriceOracle.DEFILLAMA: self.defillama,
            CurrentPriceOracle.MANUALCURRENT: self.manualcurrent,
        }
        
        self._oracle_instances = []
        for oracle in oracles:
            if oracle in instances_map:
                self._oracle_instances.append(instances_map[oracle])

    def inject_evm_managers(self, evm_managers: list[tuple[ChainID, 'EvmNodeInquirer']]) -> None:
        """Inject EVM managers for blockchain queries"""
        self._evm_managers = dict(evm_managers)

    async def get_cached_current_price_entry(
        self,
        from_asset: AssetWithOracles,
        to_asset: Asset,
    ) -> CachedPriceEntry | None:
        """Get cached price entry if not expired"""
        async with self._cache_lock:
            entry = self._cached_current_price.get((from_asset, to_asset))
            if entry and not entry.is_expired():
                return entry
            # Remove expired entry
            if entry:
                del self._cached_current_price[(from_asset, to_asset)]
            return None

    async def set_cached_price(
        self,
        from_asset: AssetWithOracles,
        to_asset: Asset,
        price: Price,
    ) -> None:
        """Cache a price entry"""
        async with self._cache_lock:
            self._cached_current_price[(from_asset, to_asset)] = CachedPriceEntry(
                price=price,
                time=ts_now(),
            )

    async def find_price(
        self,
        from_asset: Asset,
        to_asset: Asset,
        ignore_cache: bool = False,
    ) -> Price:
        """Find the current price between two assets
        
        This is the main entry point for price queries.
        """
        # Check if it's a fiat to fiat query
        if from_asset.is_fiat() and to_asset.is_fiat():
            return await self._query_fiat_pair(
                from_asset=from_asset,  # type: ignore
                to_asset=to_asset,  # type: ignore
            )
        
        # For crypto assets, check cache first
        if not ignore_cache and isinstance(from_asset, AssetWithOracles):
            cached_entry = await self.get_cached_current_price_entry(from_asset, to_asset)
            if cached_entry:
                return cached_entry.price
        
        # Query oracles for price
        if isinstance(from_asset, AssetWithOracles):
            price = await self._query_oracle_instances(from_asset, to_asset)
            if price != Price(ZERO):
                await self.set_cached_price(from_asset, to_asset, price)
                return price
        
        # Try special price queries for specific asset types
        if isinstance(from_asset, EvmToken):
            special_price = await self._find_special_token_price(from_asset, to_asset)
            if special_price != Price(ZERO):
                return special_price
        
        raise NoPriceError(
            f'Could not find price for {from_asset.identifier} to {to_asset.identifier}'
        )

    async def _query_oracle_instances(
        self,
        from_asset: AssetWithOracles,
        to_asset: Asset,
    ) -> Price:
        """Query oracle instances for price"""
        price = Price(ZERO)
        oracle_instances = list(self._oracle_instances)
        
        # Query defi oracles first if it's an LP token
        is_lp_token = (
            isinstance(from_asset, EvmToken) and 
            from_asset.protocol is not None and
            from_asset.has_oracle()
        )
        
        if is_lp_token:
            oracle_instances = self._defi_oracles + oracle_instances
        
        # Try each oracle in order
        for oracle in oracle_instances:
            try:
                price = await self._try_oracle_price_query(
                    oracle=oracle,
                    from_asset=from_asset,
                    to_asset=to_asset,
                )
                if price != Price(ZERO):
                    break
            except (PriceQueryUnsupportedAsset, RemoteError) as e:
                logger.debug(
                    f'Oracle {oracle} failed to get price for '
                    f'{from_asset.identifier} to {to_asset.identifier}: {e}'
                )
                continue
        
        return price

    async def _try_oracle_price_query(
        self,
        oracle: 'PriceOracleInstance',
        from_asset: AssetWithOracles,
        to_asset: Asset,
    ) -> Price:
        """Try to query price from a specific oracle"""
        # Convert method calls to async
        # This is a simplified version - actual implementation would need
        # to convert each oracle's query method to async
        
        if hasattr(oracle, 'query_current_price'):
            # For now, we'll need to wrap sync calls in executor
            # In a full migration, each oracle would have async methods
            loop = asyncio.get_event_loop()
            price = await loop.run_in_executor(
                None,
                oracle.query_current_price,
                from_asset,
                to_asset,
            )
            return price
        
        return Price(ZERO)

    async def _query_fiat_pair(
        self,
        from_asset: 'FiatAsset',
        to_asset: 'FiatAsset',
    ) -> Price:
        """Query exchange rate between two fiat currencies"""
        # This would use an async forex API client
        # For now, returning a mock value
        if from_asset.identifier == to_asset.identifier:
            return Price(ONE)
            
        # In real implementation, would call async forex API
        # For example: await self.forex_client.get_rate(from_asset, to_asset)
        return Price(FVal('1.1'))  # Mock exchange rate

    async def _find_special_token_price(
        self,
        token: EvmToken,
        to_asset: Asset,
    ) -> Price:
        """Find price for special token types (LP tokens, etc.)"""
        # Check if it's a known LP token type
        underlying_tokens = GlobalDBHandler.get_underlying_tokens(token.evm_address)
        
        if underlying_tokens and token.protocol:
            # Try protocol-specific price methods
            price_method_map = {
                'curve': self._find_curve_pool_price,
                'yearn': self._find_yearn_price,
                'gearbox': self._find_gearbox_price,
                'hop': self._find_hop_lp_price,
            }
            
            method = price_method_map.get(token.protocol.lower())
            if method:
                return await method(token, to_asset)
        
        return Price(ZERO)

    async def _find_curve_pool_price(
        self,
        token: EvmToken,
        to_asset: Asset,
    ) -> Price:
        """Find price for Curve LP tokens"""
        # This would implement async contract calls
        # Simplified version for now
        return Price(ZERO)

    async def _find_yearn_price(
        self,
        token: EvmToken,
        to_asset: Asset,
    ) -> Price:
        """Find price for Yearn vault tokens"""
        # This would implement async contract calls
        # Simplified version for now
        return Price(ZERO)

    async def _find_gearbox_price(
        self,
        token: EvmToken,
        to_asset: Asset,
    ) -> Price:
        """Find price for Gearbox tokens"""
        # This would implement async contract calls
        # Simplified version for now
        return Price(ZERO)

    async def _find_hop_lp_price(
        self,
        token: EvmToken,
        to_asset: Asset,
    ) -> Price:
        """Find price for Hop LP tokens"""
        # This would implement async contract calls
        # Simplified version for now
        return Price(ZERO)

    async def find_usd_price(
        self,
        asset: Asset,
        ignore_cache: bool = False,
    ) -> Price:
        """Find USD price for an asset"""
        # Get USD asset
        from rotkehlchen.constants.assets import A_USD
        
        return await self.find_price(
            from_asset=asset,
            to_asset=A_USD,
            ignore_cache=ignore_cache,
        )

    async def find_asset_price(
        self,
        from_asset: Asset,
        to_asset: Asset,
        ignore_cache: bool = False,
        at_timestamp: Timestamp | None = None,
    ) -> tuple[Price, bool]:
        """Find price between assets, optionally at a specific timestamp
        
        Returns:
            Tuple of (price, is_current_price)
        """
        if at_timestamp is None:
            # Current price query
            price = await self.find_price(from_asset, to_asset, ignore_cache)
            return price, True
        
        # Historical price query
        price = await self.find_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=at_timestamp,
        )
        return price, False

    async def find_historical_price(
        self,
        from_asset: Asset,
        to_asset: Asset,
        timestamp: Timestamp,
    ) -> Price:
        """Find historical price at a specific timestamp"""
        # This would delegate to PriceHistorian or historical oracles
        # For now, return current price as placeholder
        return await self.find_price(from_asset, to_asset)

    async def query_tokens_for_addresses(
        self,
        chain_id: ChainID,
        addresses: Sequence[ChecksumEvmAddress],
        token_kinds: Sequence[EvmTokenKind] | None = None,
    ) -> list[EvmToken]:
        """Query token information for given addresses"""
        if chain_id not in self._evm_managers:
            return []
        
        evm_inquirer = self._evm_managers[chain_id]
        tokens = []
        
        for address in addresses:
            # This would be converted to async contract calls
            # For now, using sync version wrapped in executor
            loop = asyncio.get_event_loop()
            token_data = await loop.run_in_executor(
                None,
                evm_inquirer.get_erc20_contract_info,
                address,
            )
            
            if token_data:
                token = get_or_create_evm_token(
                    chain_id=chain_id,
                    address=address,
                    symbol=token_data.get('symbol', '???'),
                    name=token_data.get('name', 'Unknown'),
                    decimals=token_data.get('decimals', 18),
                )
                
                if token_kinds is None or token.kind in token_kinds:
                    tokens.append(token)
        
        return tokens

    async def query_historical_fiat_exchange_rates(
        self,
        from_fiat_asset: 'FiatAsset',
        to_fiat_asset: 'FiatAsset',
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> list[tuple[Timestamp, Price]]:
        """Query historical exchange rates between fiat currencies"""
        # This would use an async forex history API
        # For now, return mock data
        rates = []
        
        # Generate daily rates for the range
        current_ts = from_timestamp
        base_rate = FVal('1.1')
        
        while current_ts <= to_timestamp:
            # Add some variation
            variation = FVal(0.01 * (current_ts % 10 - 5))
            rate = base_rate + variation
            rates.append((current_ts, Price(rate)))
            current_ts += DAY_IN_SECONDS
        
        return rates

    def get_oracles(self) -> list[CurrentPriceOracle]:
        """Get the configured oracle order"""
        return self._oracles.copy()

    def get_oracle_instances(self) -> list['PriceOracleInstance']:
        """Get the oracle instances"""
        return self._oracle_instances.copy()

    async def close(self) -> None:
        """Cleanup resources"""
        if self.http_client:
            await self.http_client.close()