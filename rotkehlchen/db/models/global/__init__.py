"""Global database ORM models using SQLModel

This module exports all global database models for easy importing.
Example:
    from rotkehlchen.db.models.global import GlobalAsset, EvmToken, PriceHistory
"""

# Base class
from rotkehlchen.db.models.global.base import Base

# Enums
from rotkehlchen.db.models.global.enums import AssetType, PriceHistorySourceType, TokenKind

# Asset models
from rotkehlchen.db.models.global.assets import (
    AssetCollection,
    CommonAssetDetails,
    CustomAsset,
    EvmToken,
    GlobalAsset,
    MultiassetMapping,
    UnderlyingTokensList,
    UserOwnedAsset,
)

# Mapping models
from rotkehlchen.db.models.global.mappings import (
    CounterpartyAssetMapping,
    LocationAssetMapping,
    LocationUnsupportedAsset,
)

# Cache models
from rotkehlchen.db.models.global.cache import GeneralCache, PriceHistory, UniqueCache

# Contract models
from rotkehlchen.db.models.global.contracts import ContractABI, ContractData

# Settings models
from rotkehlchen.db.models.global.settings import DefaultRPCNode, GlobalSettings

# Miscellaneous models
from rotkehlchen.db.models.global.misc import BinancePair, GlobalAddressBook

__all__ = [
    # Base
    'Base',
    # Enums
    'AssetType',
    'PriceHistorySourceType',
    'TokenKind',
    # Asset models
    'AssetCollection',
    'CommonAssetDetails',
    'CustomAsset',
    'EvmToken',
    'GlobalAsset',
    'MultiassetMapping',
    'UnderlyingTokensList',
    'UserOwnedAsset',
    # Mapping models
    'CounterpartyAssetMapping',
    'LocationAssetMapping',
    'LocationUnsupportedAsset',
    # Cache models
    'GeneralCache',
    'PriceHistory',
    'UniqueCache',
    # Contract models
    'ContractABI',
    'ContractData',
    # Settings models
    'DefaultRPCNode',
    'GlobalSettings',
    # Miscellaneous models
    'BinancePair',
    'GlobalAddressBook',
]