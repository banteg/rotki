"""User database ORM models using SQLModel

This module exports all user database models for easy importing.
Example:
    from rotkehlchen.db.models.user import Asset, BlockchainAccount, NFT
"""

# Base class
# Accounting models
from rotkehlchen.db.models.user.accounting import AccountingRule, LinkedRuleProperty

# Account models
from rotkehlchen.db.models.user.accounts import (
    BlockchainAccount,
    EvmAccountDetails,
    UserCredentialMapping,
    UserCredentials,
)

# Address book models
from rotkehlchen.db.models.user.address_book import AddressBook
from rotkehlchen.db.models.user.base import Base

# Cache models
from rotkehlchen.db.models.user.cache import KeyValueCache, MultiSettings, UsedQueryRange

# Calendar models
from rotkehlchen.db.models.user.calendar import Calendar, CalendarReminder

# Conflict models
from rotkehlchen.db.models.user.conflicts import UnresolvedRemoteConflict

# DeFi models
from rotkehlchen.db.models.user.defi import CowswapOrder, GnosisPayData

# ENS models
from rotkehlchen.db.models.user.ens import ENSMapping

# Enums
from rotkehlchen.db.models.user.enums import BalanceCategory, Location, ZkSyncLiteTxType

# EVM models
from rotkehlchen.db.models.user.evm import (
    EvmInternalTransaction,
    EvmTransaction,
    EvmTransactionAuthorization,
    EvmTxAddressMapping,
    EvmTxMapping,
    EvmTxReceipt,
    EvmTxReceiptLog,
    EvmTxReceiptLogTopic,
    OptimismTransaction,
)

# History models
from rotkehlchen.db.models.user.history import (
    EvmEventInfo,
    HistoryEvent,
    HistoryEventMapping,
    SkippedExternalEvent,
)

# Core models
from rotkehlchen.db.models.user.models import (
    Asset,
    IgnoredAction,
    ManuallyTrackedBalance,
    Settings,
    Tag,
    TagMapping,
    TimedBalance,
    TimedLocationData,
)

# NFT models
from rotkehlchen.db.models.user.nfts import NFT

# Node models
from rotkehlchen.db.models.user.nodes import RPCNode

# Note models
from rotkehlchen.db.models.user.notes import UserNote

# Service models
from rotkehlchen.db.models.user.services import ExternalServiceCredentials

# Staking models
from rotkehlchen.db.models.user.staking import (
    Eth2DailyStakingDetails,
    Eth2Validator,
    EthStakingEventInfo,
    EthValidatorsDataCache,
)

# Trading models
from rotkehlchen.db.models.user.trading import MarginPosition

# Xpub models
from rotkehlchen.db.models.user.xpubs import Xpub, XpubMapping

# zkSync Lite models
from rotkehlchen.db.models.user.zksynclite import ZkSyncLiteSwap, ZkSyncLiteTransaction

__all__ = [
    # NFT models
    'NFT',
    # Accounting models
    'AccountingRule',
    # Address book models
    'AddressBook',
    # Core models
    'Asset',
    # Enums
    'BalanceCategory',
    # Base
    'Base',
    # Account models
    'BlockchainAccount',
    # Calendar models
    'Calendar',
    'CalendarReminder',
    # DeFi models
    'CowswapOrder',
    # ENS models
    'ENSMapping',
    'EvmAccountDetails',
    # Service models
    'ExternalServiceCredentials',
    'GnosisPayData',
    'IgnoredAction',
    # Cache models
    'KeyValueCache',
    'LinkedRuleProperty',
    'Location',
    'ManuallyTrackedBalance',
    # Trading models
    'MarginPosition',
    'MultiSettings',
    # Node models
    'RPCNode',
    'Tag',
    'TagMapping',
    'TimedBalance',
    'TimedLocationData',
    # Conflict models
    'UnresolvedRemoteConflict',
    'UsedQueryRange',
    'UserCredentialMapping',
    'UserCredentials',
    # Note models
    'UserNote',
    'Settings',
    # Xpub models
    'Xpub',
    'XpubMapping',
    'ZkSyncLiteTxType',
    # EVM models
    'EvmTransaction',
    'EvmTxReceipt',
    'EvmTxReceiptLog',
    'EvmTxReceiptLogTopic',
    'EvmInternalTransaction',
    'EvmTxMapping',
    'EvmTxAddressMapping',
    'OptimismTransaction',
    'EvmTransactionAuthorization',
    # History models
    'HistoryEvent',
    'HistoryEventMapping',
    'EvmEventInfo',
    'SkippedExternalEvent',
    # Staking models
    'Eth2Validator',
    'Eth2DailyStakingDetails',
    'EthStakingEventInfo',
    'EthValidatorsDataCache',
    # zkSync Lite models
    'ZkSyncLiteTransaction',
    'ZkSyncLiteSwap',
]
