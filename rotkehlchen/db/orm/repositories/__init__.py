"""Repository layer for data access"""

from .accounts import (
    BlockchainAccountRepository,
    CredentialsRepository,
    EvmAccountDetailsRepository,
    TagRepository,
    XpubRepository,
)
from .assets import AssetRepository, OwnedAssetsRepository
from .balances import ManualBalanceRepository, TimedBalanceRepository
from .base import BaseRepository
from .defi import CowswapRepository, GnosisPayRepository
from .eth2 import ETH2StakingRepository, ETH2ValidatorRepository
from .globaldb import (
    AssetCollectionRepository,
    AssetMappingRepository,
    AssetUpdateRepository,
    PriceHistoryRepository,
)
from .history import EvmTransactionRepository, HistoryEventRepository
from .infrastructure import (
    DatabaseInfoRepository,
    LocationDataRepository,
    PremiumRepository,
)
from .nft import NFTRepository
from .settings import CacheRepository, SettingsRepository
from .trading import MarginPositionRepository, QueryRangeRepository
from .transient import ABICacheRepository, AddressBookRepository, CalendarRepository
from .unit_of_work import UnitOfWork
from .user_features import RPCNodeRepository, UserNoteRepository

__all__ = [
    # Transient
    'ABICacheRepository',
    'AddressBookRepository',
    # Global DB
    'AssetCollectionRepository',
    'AssetMappingRepository',
    # Assets
    'AssetRepository',
    'AssetUpdateRepository',
    # Base
    'BaseRepository',
    # Accounts
    'BlockchainAccountRepository',
    'CacheRepository',
    'CalendarRepository',
    # DeFi
    'CowswapRepository',
    'CredentialsRepository',
    'DatabaseInfoRepository',
    'ETH2StakingRepository',
    # ETH2
    'ETH2ValidatorRepository',
    'EvmAccountDetailsRepository',
    'EvmTransactionRepository',
    'GnosisPayRepository',
    # History
    'HistoryEventRepository',
    'LocationDataRepository',
    # Balances
    'ManualBalanceRepository',
    # Trading
    'MarginPositionRepository',
    # NFT
    'NFTRepository',
    'OwnedAssetsRepository',
    # Infrastructure
    'PremiumRepository',
    'PriceHistoryRepository',
    'QueryRangeRepository',
    'RPCNodeRepository',
    # Settings
    'SettingsRepository',
    'TagRepository',
    'TimedBalanceRepository',
    'UnitOfWork',
    # User Features
    'UserNoteRepository',
    'XpubRepository',
]
