"""User database ORM models using SQLModel

This module exports all user database models for easy importing.
Example:
    from rotkehlchen.db.models.user import Asset, BlockchainAccount, NFT
"""

# Base class
from rotkehlchen.db.models.user.base import Base

# Enums
from rotkehlchen.db.models.user.enums import BalanceCategory, Location, ZkSyncLiteTxType

# Core models
from rotkehlchen.db.models.user.models import (
    Asset,
    IgnoredAction,
    ManuallyTrackedBalance,
    Tag,
    TimedBalance,
    TimedLocationData,
    UserSettings,
)

# Account models
from rotkehlchen.db.models.user.accounts import (
    BlockchainAccount,
    EvmAccountDetails,
    UserCredentialMapping,
    UserCredentials,
)

# Xpub models
from rotkehlchen.db.models.user.xpubs import Xpub, XpubMapping

# NFT models
from rotkehlchen.db.models.user.nfts import NFT

# Service models
from rotkehlchen.db.models.user.services import ExternalServiceCredentials

# Trading models
from rotkehlchen.db.models.user.trading import MarginPosition

# Node models
from rotkehlchen.db.models.user.nodes import RPCNode

# Cache models
from rotkehlchen.db.models.user.cache import KeyValueCache, MultiSettings, UsedQueryRange

# Note models
from rotkehlchen.db.models.user.notes import UserNote

# ENS models
from rotkehlchen.db.models.user.ens import ENSMapping

# DeFi models
from rotkehlchen.db.models.user.defi import CowswapOrder, GnosisPayData

# Accounting models
from rotkehlchen.db.models.user.accounting import AccountingRule, LinkedRuleProperty

# Calendar models
from rotkehlchen.db.models.user.calendar import Calendar, CalendarReminder

# Conflict models
from rotkehlchen.db.models.user.conflicts import UnresolvedRemoteConflict

# Address book models
from rotkehlchen.db.models.user.address_book import AddressBook

__all__ = [
    # Base
    'Base',
    # Enums
    'BalanceCategory',
    'Location',
    'ZkSyncLiteTxType',
    # Core models
    'Asset',
    'IgnoredAction',
    'ManuallyTrackedBalance',
    'Tag',
    'TimedBalance',
    'TimedLocationData',
    'UserSettings',
    # Account models
    'BlockchainAccount',
    'EvmAccountDetails',
    'UserCredentialMapping',
    'UserCredentials',
    # Xpub models
    'Xpub',
    'XpubMapping',
    # NFT models
    'NFT',
    # Service models
    'ExternalServiceCredentials',
    # Trading models
    'MarginPosition',
    # Node models
    'RPCNode',
    # Cache models
    'KeyValueCache',
    'MultiSettings',
    'UsedQueryRange',
    # Note models
    'UserNote',
    # ENS models
    'ENSMapping',
    # DeFi models
    'CowswapOrder',
    'GnosisPayData',
    # Accounting models
    'AccountingRule',
    'LinkedRuleProperty',
    # Calendar models
    'Calendar',
    'CalendarReminder',
    # Conflict models
    'UnresolvedRemoteConflict',
    # Address book models
    'AddressBook',
]