"""SQLAlchemy ORM models for rotkehlchen database"""

# Base setup
from rotkehlchen.db.orm.base import (
    Base,
    GeventSafeDatabase,
    GlobalDBBase,
    TransientDBBase,
    UserDBBase,
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

# ETH2 models
from rotkehlchen.db.orm.eth2 import (
    Eth2DailyStakingDetails,
    Eth2Validator,
    EthValidatorsDataCache,
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

# History event models
from rotkehlchen.db.orm.history_events import (
    EthStakingEventInfo,
    EvmEventInfo,
    HistoryEvent,
    HistoryEventMapping,
    SkippedExternalEvent,
)

# Core models
from rotkehlchen.db.orm.models import (
    Asset,
    BlockchainAccount,
    ManuallyTrackedBalance,
    UserSettings,
    Tag,
    TimedBalance,
    UserCredentialMapping,
    UserCredentials,
)

# NFT models
from rotkehlchen.db.orm.nfts import NFT

# Protocol models
from rotkehlchen.db.orm.protocols import (
    CowswapOrder,
    GnosisPayData,
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

# Transient database models
from rotkehlchen.db.orm.transient_db_models import (
    PnlEvent,
    PnlReport,
    PnlReportSetting,
    PnlReportTotal,
    TransientSettings,
)

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

__all__ = [
    # NFT
    'NFT',
    'AccountingRule',
    'AddressBook',
    'Asset',
    'AssetCollection',
    'AssetType',
    'BalanceCategory',
    # Base
    'Base',
    'UserDBBase',
    'GlobalDBBase',
    'TransientDBBase',
    'BinancePair',
    'BlockchainAccount',
    'Calendar',
    'CalendarReminder',
    'CommonAssetDetails',
    'ContractABI',
    'ContractData',
    'CounterpartyAssetMapping',
    # Protocols
    'CowswapOrder',
    'CustomAsset',
    'DefaultRPCNode',
    'ENSMapping',
    'Eth2DailyStakingDetails',
    # ETH2
    'Eth2Validator',
    'EthStakingEventInfo',
    'EthValidatorsDataCache',
    'EvmAccountDetails',
    'EvmEventInfo',
    'EvmInternalTransaction',
    'EvmToken',
    # Transactions
    'EvmTransaction',
    'EvmTxAddressMapping',
    'EvmTxMapping',
    'EvmTxReceipt',
    'EvmTxReceiptLog',
    'EvmTxReceiptLogTopic',
    # Additional user DB
    'ExternalServiceCredentials',
    'GeneralCache',
    'GeventSafeDatabase',
    'GlobalAddressBook',
    # Global DB
    'GlobalAsset',
    'GlobalSettings',
    'GnosisPayData',
    # History events
    'HistoryEvent',
    'HistoryEventMapping',
    'IgnoredAction',
    'KeyValueCache',
    'LinkedRuleProperty',
    # Enums
    'Location',
    'LocationAssetMapping',
    'LocationUnsupportedAsset',
    'ManuallyTrackedBalance',
    'MarginPosition',
    'MultiSettings',
    'MultiassetMapping',
    'OptimismTransaction',
    'PnlEvent',
    # Transient DB
    'PnlReport',
    'PnlReportSetting',
    'PnlReportTotal',
    'PriceHistory',
    'PriceHistorySourceType',
    'RPCNode',
    # Core models
    'UserSettings',
    'SkippedExternalEvent',
    'Tag',
    'TimedBalance',
    'TokenKind',
    'TransientSettings',
    'UnderlyingTokensList',
    'UniqueCache',
    'UnresolvedRemoteConflict',
    'UsedQueryRange',
    'UserCredentialMapping',
    'UserCredentials',
    'UserNote',
    'UserOwnedAsset',
    'Xpub',
    'XpubMapping',
    'ZkSyncLiteSwap',
    # ZkSync
    'ZkSyncLiteTransaction',
    'ZkSyncLiteTxType',
    'get_global_db',
    'get_transient_db',
    'get_user_db',
    'init_global_db',
    'init_transient_db',
    'init_user_db',
]
