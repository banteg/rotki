"""Central repository manager for easy access to all repositories"""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from rotkehlchen.db.orm.repositories import (
    ABICacheRepository,
    AddressBookRepository,
    AssetCollectionRepository,
    AssetMappingRepository,
    AssetRepository,
    # AssetUpdateRepository,  # TODO: Add AssetUpdate model
    BlockchainAccountRepository,
    CacheRepository,
    CalendarRepository,
    CowswapRepository,
    CredentialsRepository,
    # DatabaseInfoRepository,  # TODO: Add DBInfo model
    # ETH2StakingRepository,  # TODO: Fix model mismatch
    # ETH2ValidatorRepository,  # TODO: Fix model mismatch
    EvmAccountDetailsRepository,
    EvmTransactionRepository,
    GnosisPayRepository,
    HistoryEventRepository,
    # LocationDataRepository,  # TODO: Add LocationData model
    ManualBalanceRepository,
    MarginPositionRepository,
    NFTRepository,
    OwnedAssetsRepository,
    # PremiumRepository,  # TODO: Add premium models
    PriceHistoryRepository,
    QueryRangeRepository,
    RPCNodeRepository,
    SettingsRepository,
    TagRepository,
    TimedBalanceRepository,
    UnitOfWork,
    UserNoteRepository,
    XpubRepository,
)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


class RepositoryManager:
    """
    Central manager providing access to all repositories.

    This class acts as a facade to simplify repository access
    and ensure consistent session management.
    """

    def __init__(self, session: Session):
        """Initialize repository manager with database session"""
        self.session = session
        self._init_repositories()

    def _init_repositories(self) -> None:
        """Initialize all repository instances"""
        # Account repositories
        self.accounts = BlockchainAccountRepository(self.session)
        self.tags = TagRepository(self.session)
        self.xpubs = XpubRepository(self.session)
        self.evm_account_details = EvmAccountDetailsRepository(self.session)
        self.credentials = CredentialsRepository(self.session)

        # Asset repositories
        self.assets = AssetRepository(self.session)
        self.owned_assets = OwnedAssetsRepository(self.session)

        # Balance repositories
        self.manual_balances = ManualBalanceRepository(self.session)
        self.timed_balances = TimedBalanceRepository(self.session)

        # Trading repositories
        self.margin_positions = MarginPositionRepository(self.session)
        self.query_ranges = QueryRangeRepository(self.session)

        # History repositories
        self.history_events = HistoryEventRepository(self.session)
        self.evm_transactions = EvmTransactionRepository(self.session)

        # Settings repositories
        self.settings = SettingsRepository(self.session)
        self.cache = CacheRepository(self.session)

        # User feature repositories
        self.user_notes = UserNoteRepository(self.session)
        self.rpc_nodes = RPCNodeRepository(self.session)

        # ETH2 repositories
        # self.eth2_validators = ETH2ValidatorRepository(self.session)  # TODO: Fix model mismatch
        # self.eth2_staking = ETH2StakingRepository(self.session)  # TODO: Fix model mismatch

        # DeFi repositories
        self.cowswap = CowswapRepository(self.session)
        self.gnosis_pay = GnosisPayRepository(self.session)

        # NFT repository
        self.nfts = NFTRepository(self.session)

        # Infrastructure repositories
        # self.premium = PremiumRepository(self.session)  # TODO: Add premium models
        # self.location_data = LocationDataRepository(self.session)  # TODO: Add LocationData model
        # self.database_info = DatabaseInfoRepository(self.session)  # TODO: Add DBInfo model

        # Global database repositories
        self.asset_collections = AssetCollectionRepository(self.session)
        self.asset_mappings = AssetMappingRepository(self.session)
        # self.asset_updates = AssetUpdateRepository(self.session)  # TODO: Add AssetUpdate model
        self.price_history = PriceHistoryRepository(self.session)

        # Transient database repositories
        self.abi_cache = ABICacheRepository(self.session)
        self.address_book = AddressBookRepository(self.session)
        self.calendar = CalendarRepository(self.session)

    def unit_of_work(self) -> UnitOfWork:
        """Create a new unit of work for transaction management"""
        return UnitOfWork(self.session)

    def commit(self) -> None:
        """Commit the current transaction"""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction"""
        self.session.rollback()

    def close(self) -> None:
        """Close the session"""
        self.session.close()

    @classmethod
    def from_connection(cls, connection: 'DBConnection') -> 'RepositoryManager':
        """Create repository manager from database connection"""
        return cls(connection.session)


class GlobalDBRepositoryManager(RepositoryManager):
    """Repository manager specifically for global database"""

    def _init_repositories(self) -> None:
        """Initialize only global database repositories"""
        # Only init global db repositories
        self.asset_collections = AssetCollectionRepository(self.session)
        self.asset_mappings = AssetMappingRepository(self.session)
        # self.asset_updates = AssetUpdateRepository(self.session)  # TODO: Add AssetUpdate model
        self.price_history = PriceHistoryRepository(self.session)


class TransientDBRepositoryManager(RepositoryManager):
    """Repository manager specifically for transient database"""

    def _init_repositories(self) -> None:
        """Initialize only transient database repositories"""
        # Only init transient db repositories
        self.abi_cache = ABICacheRepository(self.session)
        self.address_book = AddressBookRepository(self.session)
        self.calendar = CalendarRepository(self.session)
