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
from .history import HistoryEventRepository, EvmTransactionRepository
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
    # Base
    'BaseRepository',
    'UnitOfWork',
    # Accounts
    'BlockchainAccountRepository',
    'TagRepository',
    'XpubRepository',
    'EvmAccountDetailsRepository',
    'CredentialsRepository',
    # Assets
    'AssetRepository',
    'OwnedAssetsRepository',
    # Balances
    'ManualBalanceRepository',
    'TimedBalanceRepository',
    # Trading
    'MarginPositionRepository',
    'QueryRangeRepository',
    # History
    'HistoryEventRepository',
    'EvmTransactionRepository',
    # Settings
    'SettingsRepository',
    'CacheRepository',
    # User Features
    'UserNoteRepository',
    'RPCNodeRepository',
    # ETH2
    'ETH2ValidatorRepository',
    'ETH2StakingRepository',
    # DeFi
    'CowswapRepository',
    'GnosisPayRepository',
    # NFT
    'NFTRepository',
    # Infrastructure
    'PremiumRepository',
    'LocationDataRepository',
    'DatabaseInfoRepository',
    # Global DB
    'AssetCollectionRepository',
    'AssetMappingRepository',
    'AssetUpdateRepository',
    'PriceHistoryRepository',
    # Transient
    'ABICacheRepository',
    'AddressBookRepository',
    'CalendarRepository',
]