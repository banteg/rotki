"""Oracles service for managing price oracles"""
from typing import Any, TYPE_CHECKING

from rotkehlchen.history.price import HistoricalPriceOracle

if TYPE_CHECKING:
    pass


class OraclesService:
    """Service for managing price oracles"""
    
    def __init__(self) -> None:
        # Would be initialized from app state
        self._supported_oracles = [
            HistoricalPriceOracle.COINGECKO,
            HistoricalPriceOracle.CRYPTOCOMPARE,
            HistoricalPriceOracle.DEFILLAMA,
            HistoricalPriceOracle.MANUAL,
        ]
        self._oracle_cache: dict[str, dict[str, Any]] = {}
    
    def get_supported_oracles(self) -> list[str]:
        """Get list of supported oracles"""
        return [oracle.value.lower() for oracle in self._supported_oracles]
    
    def get_oracle_cache(self, oracle: str, async_query: bool = False) -> dict[str, Any] | None:
        """Get cache data for a specific oracle"""
        try:
            oracle_enum = HistoricalPriceOracle(oracle.upper())
        except ValueError:
            return None
        
        if oracle_enum not in self._supported_oracles:
            return None
        
        # Would actually get real cache data from DB
        return {
            'oracle': oracle,
            'cache_data': [],  # Would contain actual cache entries
        }
    
    def create_oracle_cache(
        self,
        oracle: str,
        from_asset: str,
        to_asset: str,
        purge_old: bool = False,
        async_query: bool = False,
    ) -> dict[str, Any]:
        """Create cache for a specific oracle"""
        try:
            oracle_enum = HistoricalPriceOracle(oracle.upper())
        except ValueError:
            raise ValueError(f'Invalid oracle: {oracle}')
        
        if oracle_enum not in self._supported_oracles:
            raise ValueError(f'Unsupported oracle: {oracle}')
        
        # Would actually create cache entries in DB
        return {
            'oracle': oracle,
            'from_asset': from_asset,
            'to_asset': to_asset,
            'entries_created': 10,  # Simulated
        }
    
    def delete_oracle_cache(
        self,
        oracle: str,
        from_asset: str,
        to_asset: str,
    ) -> None:
        """Delete cache for a specific oracle and asset pair"""
        try:
            oracle_enum = HistoricalPriceOracle(oracle.upper())
        except ValueError:
            raise ValueError(f'Invalid oracle: {oracle}')
        
        if oracle_enum not in self._supported_oracles:
            raise ValueError(f'Unsupported oracle: {oracle}')
        
        # Would actually delete cache entries from DB
        pass