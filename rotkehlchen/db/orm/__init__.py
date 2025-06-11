"""SQLAlchemy ORM models for rotkehlchen database"""

# Base setup
from rotkehlchen.db.orm.base import (
    Base,
    GeventSafeDatabase,
    get_global_db,
    get_transient_db,
    get_user_db,
    init_global_db,
    init_transient_db,
    init_user_db,
)

# Enum models
from rotkehlchen.db.orm.enums import (
    AssetType,
    BalanceCategory,
    Location,
    PriceHistorySourceType,
    TokenKind,
    ZkSyncLiteTxType,
)

# Core models
from rotkehlchen.db.orm.models import (
    Asset,
    BlockchainAccount,
    ManuallyTrackedBalance,
    Settings,
    Tag,
    TimedBalance,
    UserCredentialMapping,
    UserCredentials,
)

# Transaction models
from rotkehlchen.db.orm.transactions import (
    EvmInternalTransaction,
    EvmTransaction,
    EvmTxAddressMapping,
    EvmTxMapping,
    EvmTxReceipt,
    EvmTxReceiptLog,
    EvmTxReceiptLogTopic,
    OptimismTransaction,
)

# History event models
from rotkehlchen.db.orm.history_events import (
    EthStakingEventInfo,
    EvmEventInfo,
    HistoryEvent,
    HistoryEventMapping,
    SkippedExternalEvent,
)

# ETH2 models
from rotkehlchen.db.orm.eth2 import (
    Eth2DailyStakingDetails,
    Eth2Validator,
    EthValidatorsDataCache,
)

# NFT models
from rotkehlchen.db.orm.nfts import NFT

# Additional user database models
from rotkehlchen.db.orm.user_db_models import (
    AccountingRule,
    AddressBook,
    Calendar,
    CalendarReminder,
    ENSMapping,
    EvmAccountDetails,
    ExternalServiceCredentials,
    IgnoredAction,
    KeyValueCache,
    LinkedRuleProperty,
    MarginPosition,
    MultiSettings,
    RPCNode,
    UnresolvedRemoteConflict,
    UsedQueryRange,
    UserNote,
    Xpub,
    XpubMapping,
)

# ZkSync models
from rotkehlchen.db.orm.zksync import (
    ZkSyncLiteSwap,
    ZkSyncLiteTransaction,
)

# Protocol models
from rotkehlchen.db.orm.protocols import (
    CowswapOrder,
    GnosisPayData,
)

# Global database models
from rotkehlchen.db.orm.global_db_models import (
    AssetCollection,
    BinancePair,
    CommonAssetDetails,
    ContractABI,
    ContractData,
    CounterpartyAssetMapping,
    CustomAsset,
    DefaultRPCNode,
    EvmToken,
    GeneralCache,
    GlobalAddressBook,
    GlobalAsset,
    GlobalSettings,
    LocationAssetMapping,
    LocationUnsupportedAsset,
    MultiassetMapping,
    PriceHistory,
    UnderlyingTokensList,
    UniqueCache,
    UserOwnedAsset,
)

# Transient database models
from rotkehlchen.db.orm.transient_db_models import (
    PnlEvent,
    PnlReport,
    PnlReportSetting,
    PnlReportTotal,
    TransientSettings,
)

__all__ = [
    # Base
    'Base',
    'GeventSafeDatabase',
    'get_user_db',
    'get_global_db',
    'get_transient_db',
    'init_user_db',
    'init_global_db',
    'init_transient_db',
    # Enums
    'Location',
    'BalanceCategory',
    'AssetType',
    'TokenKind',
    'PriceHistorySourceType',
    'ZkSyncLiteTxType',
    # Core models
    'Settings',
    'Asset',
    'Tag',
    'UserCredentials',
    'UserCredentialMapping',
    'BlockchainAccount',
    'TimedBalance',
    'ManuallyTrackedBalance',
    # Transactions
    'EvmTransaction',
    'EvmInternalTransaction',
    'EvmTxReceipt',
    'EvmTxReceiptLog',
    'EvmTxReceiptLogTopic',
    'OptimismTransaction',
    'EvmTxAddressMapping',
    'EvmTxMapping',
    # History events
    'HistoryEvent',
    'EvmEventInfo',
    'EthStakingEventInfo',
    'HistoryEventMapping',
    'SkippedExternalEvent',
    # ETH2
    'Eth2Validator',
    'EthValidatorsDataCache',
    'Eth2DailyStakingDetails',
    # NFT
    'NFT',
    # Additional user DB
    'ExternalServiceCredentials',
    'Xpub',
    'XpubMapping',
    'EvmAccountDetails',
    'MarginPosition',
    'UsedQueryRange',
    'MultiSettings',
    'IgnoredAction',
    'ENSMapping',
    'AddressBook',
    'RPCNode',
    'UserNote',
    'AccountingRule',
    'LinkedRuleProperty',
    'UnresolvedRemoteConflict',
    'KeyValueCache',
    'Calendar',
    'CalendarReminder',
    # ZkSync
    'ZkSyncLiteTransaction',
    'ZkSyncLiteSwap',
    # Protocols
    'CowswapOrder',
    'GnosisPayData',
    # Global DB
    'GlobalAsset',
    'CommonAssetDetails',
    'EvmToken',
    'UnderlyingTokensList',
    'CustomAsset',
    'AssetCollection',
    'MultiassetMapping',
    'UserOwnedAsset',
    'PriceHistory',
    'BinancePair',
    'LocationAssetMapping',
    'CounterpartyAssetMapping',
    'LocationUnsupportedAsset',
    'GlobalSettings',
    'GlobalAddressBook',
    'DefaultRPCNode',
    'GeneralCache',
    'UniqueCache',
    'ContractABI',
    'ContractData',
    # Transient DB
    'PnlReport',
    'PnlReportTotal',
    'PnlReportSetting',
    'PnlEvent',
    'TransientSettings',
]