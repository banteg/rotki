"""Alembic environment configuration for Rotkehlchen ORM"""

import logging
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add rotkehlchen to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from rotkehlchen.db.orm import Base
from rotkehlchen.db.orm.base import GeventSafeDatabase

# Import all models to ensure they're registered with Base.metadata
from rotkehlchen.db.orm import (
    # User DB models
    AccountingRule, AddressBook, Asset, BlockchainAccount, Calendar,
    CalendarReminder, CowswapOrder, ENSMapping, Eth2DailyStakingDetails,
    Eth2Validator, EthStakingEventInfo, EthValidatorsDataCache, EvmAccountDetails,
    EvmEventInfo, EvmInternalTransaction, EvmTransaction, EvmTxAddressMapping,
    EvmTxMapping, EvmTxReceipt, EvmTxReceiptLog, EvmTxReceiptLogTopic,
    ExternalServiceCredentials, GnosisPayData, HistoryEvent, HistoryEventMapping,
    IgnoredAction, KeyValueCache, LinkedRuleProperty, ManuallyTrackedBalance,
    MarginPosition, MultiSettings, NFT, OptimismTransaction, RPCNode, Settings,
    SkippedExternalEvent, Tag, TimedBalance, UnresolvedRemoteConflict,
    UsedQueryRange, UserCredentialMapping, UserCredentials, UserNote, Xpub,
    XpubMapping, ZkSyncLiteSwap, ZkSyncLiteTransaction,
    # Global DB models
    AssetCollection, BinancePair, CommonAssetDetails, ContractABI, ContractData,
    CounterpartyAssetMapping, CustomAsset, DefaultRPCNode, EvmToken, GeneralCache,
    GlobalAddressBook, GlobalAsset, GlobalSettings, LocationAssetMapping,
    LocationUnsupportedAsset, MultiassetMapping, PriceHistory, UnderlyingTokensList,
    UniqueCache, UserOwnedAsset,
    # Transient DB models
    PnlEvent, PnlReport, PnlReportSetting, PnlReportTotal, TransientSettings,
    # Enum models
    AssetType, BalanceCategory, Location, PriceHistorySourceType, TokenKind,
    ZkSyncLiteTxType,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """Get database URL from command line or environment"""
    # You can pass database URL via command line:
    # alembic -x db_url=sqlite:///path/to/db.db upgrade head
    db_url = context.get_x_argument(as_dictionary=True).get('db_url')
    if db_url:
        return db_url
    
    # Or use a default for development
    return "sqlite:///rotkehlchen.db"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()