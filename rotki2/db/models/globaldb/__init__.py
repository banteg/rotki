"""Global database ORM models using SQLModel

This module exports all global database models for easy importing.
Example:
    from rotki2.db.models.globaldb import GlobalAsset, EvmToken, PriceHistory
"""

# Base class
# Asset models
from rotki2.db.models.globaldb.assets import (
    AssetCollection,
    CommonAssetDetails,
    CustomAsset,
    EvmToken,
    GlobalAsset,
    MultiassetMapping,
    UnderlyingTokensList,
    UserOwnedAsset,
)
from rotki2.db.models.globaldb.base import Base

# Cache models
from rotki2.db.models.globaldb.cache import GeneralCache, PriceHistory, UniqueCache

# Contract models
from rotki2.db.models.globaldb.contracts import ContractABI, ContractData

# Enums
from rotki2.db.models.globaldb.enums import AssetType, PriceHistorySourceType, TokenKind

# Mapping models
from rotki2.db.models.globaldb.mappings import (
    CounterpartyAssetMapping,
    LocationAssetMapping,
    LocationUnsupportedAsset,
)

# Miscellaneous models
from rotki2.db.models.globaldb.misc import BinancePair, GlobalAddressBook

# Settings models
from rotki2.db.models.globaldb.settings import DefaultRPCNode, GlobalSettings

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
