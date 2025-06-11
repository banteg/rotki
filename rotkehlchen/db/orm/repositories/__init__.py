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
# from .eth2 import ETH2StakingRepository, ETH2ValidatorRepository  # TODO: Fix model mismatch
from .globaldb import (
    AssetCollectionRepository,
    AssetMappingRepository,
    # AssetUpdateRepository,  # TODO: Add AssetUpdate model
    PriceHistoryRepository,
)
from .history import EvmTransactionRepository, HistoryEventRepository
# from .infrastructure import (  # TODO: Add missing models
#     DatabaseInfoRepository,
#     LocationDataRepository,
#     PremiumRepository,
# )
from .nft import NFTRepository
from .settings import CacheRepository, SettingsRepository
from .trading import MarginPositionRepository, QueryRangeRepository
from .transient import AddressBookRepository, CalendarRepository  # ABICacheRepository - TODO
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
    # 'AssetUpdateRepository',  # TODO: Add AssetUpdate model
    # Base
    'BaseRepository',
    # Accounts
    'BlockchainAccountRepository',
    'CacheRepository',
    'CalendarRepository',
    # DeFi
    'CowswapRepository',
    'CredentialsRepository',
    # 'DatabaseInfoRepository',  # TODO: Add DBInfo model
    # 'ETH2StakingRepository',  # TODO: Fix model mismatch
    # ETH2
    # 'ETH2ValidatorRepository',  # TODO: Fix model mismatch
    'EvmAccountDetailsRepository',
    'EvmTransactionRepository',
    'GnosisPayRepository',
    # History
    'HistoryEventRepository',
    # 'LocationDataRepository',  # TODO: Add LocationData model
    # Balances
    'ManualBalanceRepository',
    # Trading
    'MarginPositionRepository',
    # NFT
    'NFTRepository',
    'OwnedAssetsRepository',
    # Infrastructure
    # 'PremiumRepository',  # TODO: Add premium models
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
