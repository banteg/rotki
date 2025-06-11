#!/usr/bin/env python
"""Rotkehlchen main application class using ORM"""

import argparse
import contextlib
import logging
import os
import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from types import FunctionType
from typing import TYPE_CHECKING, Any, Literal, Optional, cast, overload

import gevent

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, AssetWithOracles, Nft
from rotkehlchen.balances.manual import (
    account_for_manually_tracked_asset_balances,
    get_manually_tracked_balances,
)
from rotkehlchen.chain.accounts import OptionalBlockchainAccount, SingleBlockchainAccountData
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneManager
from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
from rotkehlchen.chain.avalanche.manager import AvalancheManager
from rotkehlchen.chain.base.manager import BaseManager
from rotkehlchen.chain.base.node_inquirer import BaseInquirer
from rotkehlchen.chain.binance_sc.manager import BinanceSCManager
from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.names import NamePrioritizer
from rotkehlchen.chain.evm.nodes import populate_rpc_nodes_in_database
from rotkehlchen.chain.gnosis.manager import GnosisManager
from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
from rotkehlchen.chain.optimism.manager import OptimismManager
from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
from rotkehlchen.chain.scroll.manager import ScrollManager
from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
from rotkehlchen.chain.substrate.manager import SubstrateManager
from rotkehlchen.chain.substrate.utils import (
    KUSAMA_NODES_TO_CONNECT_AT_START,
    POLKADOT_NODES_TO_CONNECT_AT_START,
)
from rotkehlchen.chain.zksync_lite.manager import ZksyncLiteManager
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.data_handler_orm import DataHandler
from rotkehlchen.data_import.manager import CSVDataImporter
from rotkehlchen.data_migrations.manager import DataMigrationManager
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import NFTFilterQuery
from rotkehlchen.db.orm.database import RotkehlchenDatabase
from rotkehlchen.db.settings import CachedSettings, DBSettings, ModifiableDBSettings
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.db.utils import replace_tag_mappings
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import (
    EthSyncError,
    GreenletKilledError,
    InputError,
    RemoteError,
    SystemPermissionError,
)
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.beaconchain.service import BeaconChain
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.asset_updates.manager import AssetsUpdater
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.history.manager import HistoryQueryingManager
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.icons import IconManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.oracles.structures import CurrentPriceOracle
from rotkehlchen.premium.premium import (
    Premium,
    PremiumCredentials,
    has_premium_check,
    premium_create_and_verify,
)
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.tasks.manager import DEFAULT_MAX_TASKS_NUM, TaskManager
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    EVM_CHAINS_WITH_TRANSACTIONS_TYPE,
    SUPPORTED_BITCOIN_CHAINS,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    SUPPORTED_SUBSTRATE_CHAINS,
    AddressbookEntry,
    AddressbookType,
    ApiKey,
    ApiSecret,
    BTCAddress,
    ChainType,
    ChecksumEvmAddress,
    ExternalService,
    ListOfBlockchainAddresses,
    Location,
    SubstrateAddress,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.usage_analytics import maybe_submit_usage_analytics
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.datadir import maybe_restructure_rotki_data_directory
from rotkehlchen.utils.misc import combine_dicts, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.exchanges.kraken import KrakenAccountType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAIN_LOOP_SECS_DELAY = 10


class Rotkehlchen:
    """Main Rotkehlchen application class using ORM database layer"""
    
    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize the Rotkehlchen object using ORM

        This runs during backend initialization so it should be as light as possible.

        May Raise:
        - SystemPermissionError if the given data directory's permissions
        are not correct.
        - DBSchemaError if GlobalDB's schema is malformed
        """
        # Can also be None after unlock if premium credentials did not
        # authenticate or premium server temporarily offline
        self.premium: Premium | None = None
        self.user_is_logged_in: bool = False

        self.args = args
        if self.args.data_dir is None:
            self.data_dir = default_data_directory()
        else:
            self.data_dir = Path(self.args.data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        maybe_restructure_rotki_data_directory(self.data_dir)

        if not os.access(self.data_dir, os.W_OK | os.R_OK):
            raise SystemPermissionError(
                f'The given data directory {self.data_dir} is not readable or writable',
            )
        self.main_loop_spawned = False
        self.api_task_greenlets: list[gevent.Greenlet] = []
        self.msg_aggregator = MessagesAggregator()
        self.greenlet_manager = GreenletManager(msg_aggregator=self.msg_aggregator)
        self.rotki_notifier = RotkiNotifier()
        self.msg_aggregator.rotki_notifier = self.rotki_notifier
        self.exchange_manager = ExchangeManager(msg_aggregator=self.msg_aggregator)
        
        # Initialize the GlobalDBHandler singleton. Has to be initialized BEFORE asset resolver
        globaldb = GlobalDBHandler(
            data_dir=self.data_dir,
            perform_assets_updates=True,
            sql_vm_instructions_cb=self.args.sqlite_instructions,
            msg_aggregator=self.msg_aggregator,
        )
        if globaldb.used_backup is True:
            self.msg_aggregator.add_warning(
                'Your global database was left in an half-upgraded state. '
                'Restored from the latest backup we could find',
            )
        
        # Initialize DataHandler with ORM
        self.data = DataHandler(
            self.data_dir,
            self.msg_aggregator,
            sql_vm_instructions_cb=args.sqlite_instructions,
        )
        
        self.cryptocompare = Cryptocompare(database=None)
        self.coingecko = Coingecko(database=None)
        self.defillama = Defillama(database=None)
        self.alchemy = Alchemy(database=None)
        self.icon_manager = IconManager(
            data_dir=self.data_dir,
            coingecko=self.coingecko,
            greenlet_manager=self.greenlet_manager,
        )

        # Initialize the Inquirer singleton
        Inquirer(
            data_dir=self.data_dir,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=self.alchemy,
            manualcurrent=ManualCurrentOracle(),
            msg_aggregator=self.msg_aggregator,
        )
        # Initialize EVM Contracts common abis
        EvmContracts.initialize_common_abis()
        self.task_manager: TaskManager | None = None
        self.shutdown_event = gevent.event.Event()
        self.migration_manager = DataMigrationManager(self)

    def _perform_new_db_actions(self) -> None:
        """Actions to perform at creation of a new DB"""
        # TODO: Use ORM to populate RPC nodes
        with self.data.db.repos.unit_of_work():
            # TODO: Implement populate_rpc_nodes_in_database with ORM
            pass

    def unlock_user(
            self,
            user: str,
            password: str,
            create_new: bool,
            sync_approval: Literal['yes', 'no', 'unknown'],
            premium_credentials: PremiumCredentials | None,
            resume_from_backup: bool,
            initial_settings: ModifiableDBSettings | None = None,
            sync_database: bool = True,
    ) -> None:
        """Unlocks an existing user or creates a new one if `create_new` is True

        May raise:
        - PremiumAuthenticationError if the password can't unlock the database.
        - AuthenticationError if premium_credentials are given and are invalid
        or can't authenticate with the server
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error or if the version is older
        than the one supported.
        - SystemPermissionError if the directory or DB file can not be accessed
        - sqlcipher.OperationalError: If some very weird error happens with the DB.
        For example unexpected schema.
        - DBSchemaError if database schema is malformed.
        """
        log.info(
            'Unlocking user',
            user=user,
            create_new=create_new,
            sync_approval=sync_approval,
            sync_database=sync_database,
            initial_settings=initial_settings,
            resume_from_backup=resume_from_backup,
        )

        # unlock or create the DB
        self.user_directory = self.data.unlock(
            username=user,
            password=password,
            create_new=create_new,
            initial_settings=initial_settings,
            resume_from_backup=resume_from_backup,
        )
        
        if create_new:
            self._perform_new_db_actions()

        # Create CSV data importer with ORM database
        self.data_importer = CSVDataImporter(db=self.data.db)
        self.premium_sync_manager = PremiumSyncManager(
            migration_manager=self.migration_manager,
            data=self.data,
        )
        
        # TODO: Set the DB in the instances that need it
        # TODO: These still need to be updated to use ORM
        # TODO: For now, we'll need to provide compatibility
        # self.cryptocompare.set_database(self.data.db)
        # self.defillama.set_database(self.data.db)
        # self.coingecko.set_database(self.data.db)
        # self.alchemy.set_database(self.data.db)
        # Inquirer()._manualcurrent.set_database(database=self.data.db)

        # Get settings using ORM
        settings = self.get_settings()
        CachedSettings().initialize(settings)
        
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='submit_usage_analytics',
            exception_is_error=False,
            method=maybe_submit_usage_analytics,
            data_dir=self.data_dir,
            should_submit=settings.submit_usage_analytics,
        )
        
        # TODO: Initialize components that need database access
        # TODO: These components need to be updated to use ORM
        # self.beaconchain = BeaconChain(database=self.data.db, msg_aggregator=self.msg_aggregator)
        
        # Get exchange credentials using ORM
        exchange_credentials = self._get_exchange_credentials()
        # TODO: Update exchange_manager to use ORM
        # self.exchange_manager.initialize_exchanges(
        #     exchange_credentials=exchange_credentials,
        #     database=self.data.db,
        # )
        
        # Get blockchain accounts using ORM
        blockchain_accounts = self._get_blockchain_accounts()
        
        # TODO: Continue with initialization...
        # TODO: The rest of the initialization code would follow similar pattern
        # TODO: converting DBHandler usage to ORM repository usage

    def get_settings(self) -> DBSettings:
        """Get user settings using ORM"""
        db = self.data.db
        settings_dict = db.repos.settings.get_all_settings()
        
        # TODO: Convert to DBSettings object
        # TODO: This requires mapping the settings appropriately
        return DBSettings(
            have_premium=bool(db.repos.premium.has_premium()),
            version=db.get_version(),
            # TODO: Map other settings from settings_dict
            # TODO: Complete settings mapping
        )

    def _get_exchange_credentials(self) -> dict[Location, list[Any]]:
        """Get exchange credentials using ORM"""
        db = self.data.db
        all_credentials = db.repos.credentials.get_all_credentials()
        
        credentials_dict = defaultdict(list)
        for cred in all_credentials:
            credentials_dict[Location.deserialize_from_db(cred.location)].append({
                'name': cred.name,
                'api_key': cred.api_key,
                'api_secret': cred.api_secret,
                'passphrase': cred.passphrase,
                'kraken_account_type': cred.kraken_account_type,
            })
        
        return dict(credentials_dict)

    def _get_blockchain_accounts(self) -> ListOfBlockchainAddresses:
        """Get blockchain accounts using ORM"""
        db = self.data.db
        all_accounts = db.repos.accounts.get_all_accounts()
        
        accounts_dict = defaultdict(list)
        for account in all_accounts:
            blockchain = SupportedBlockchain.deserialize(account.blockchain)
            accounts_dict[blockchain].append(account.account)
        
        # TODO: Convert to ListOfBlockchainAddresses
        # TODO: This requires proper initialization of the data structure
        # TODO: Complete blockchain accounts mapping
        return ListOfBlockchainAddresses()

    def logout(self) -> None:
        """Logout the current user"""
        if not self.user_is_logged_in:
            return

        log.info('Logging out user', user=self.data.username)
        
        # Cleanup and logout
        self.data.logout()
        self.user_is_logged_in = False
        
        # Reset components
        self.exchange_manager.delete_all_exchanges()
        CachedSettings().reset()

    # TODO: Additional methods would be implemented following similar patterns
    # TODO: converting from DBHandler calls to ORM repository calls