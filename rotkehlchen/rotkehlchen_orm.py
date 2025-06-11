#!/usr/bin/env python
"""Main Rotkehlchen application class using ORM"""

import argparse
import logging
import os
from collections import defaultdict
from pathlib import Path
from types import FunctionType
from typing import Any, Literal

import gevent

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.chain.accounts import OptionalBlockchainAccount
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
from rotkehlchen.chain.evm.nodes_orm import populate_rpc_nodes_in_database_orm
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
from rotkehlchen.data_handler_orm import DataHandler
from rotkehlchen.data_import.manager import CSVDataImporter
from rotkehlchen.data_migrations.manager import DataMigrationManager
from rotkehlchen.db.settings import CachedSettings, DBSettings, ModifiableDBSettings
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.misc import (
    GreenletKilledError,
    SystemPermissionError,
)
from rotkehlchen.exchanges.manager_orm import ExchangeManager
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.beaconchain.service import BeaconChain
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.globaldb.asset_updates.manager import AssetsUpdater
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.history.manager import HistoryQueryingManager
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.icons import IconManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import (
    Premium,
    PremiumCredentials,
)
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.tasks.manager import DEFAULT_MAX_TASKS_NUM, TaskManager
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    BTCAddress,
    ChecksumEvmAddress,
    ListOfBlockchainAddresses,
    Location,
    SubstrateAddress,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.usage_analytics import maybe_submit_usage_analytics
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.datadir import maybe_restructure_rotki_data_directory

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAIN_LOOP_SECS_DELAY = 10


class Rotkehlchen:
    """Main Rotkehlchen application class using ORM for database access"""

    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize the Rotkehlchen object

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

    def maybe_kill_running_tx_query_tasks(
            self,
            blockchain: SupportedBlockchain,
            addresses: list[ChecksumEvmAddress],
    ) -> None:
        """Checks for running greenlets related to transactions query for the given
        addresses and kills them if they exist"""
        assert self.task_manager is not None, 'task manager should have been initialized at this point'

        for address in addresses:
            account_data = OptionalBlockchainAccount(address=address, chain=blockchain)
            for greenlet in self.api_task_greenlets:
                is_evm_tx_greenlet = (
                    greenlet.dead is False and
                    len(greenlet.args) >= 1 and
                    isinstance(greenlet.args[0], FunctionType) and
                    greenlet.args[0].__qualname__ == 'RestAPI.refresh_transactions'
                )
                if (
                        is_evm_tx_greenlet and
                        greenlet.kwargs.get('only_cache', False) is False and
                        account_data in greenlet.kwargs['accounts']
                ):
                    greenlet.kill(exception=GreenletKilledError('Killed due to request for evm address removal'))

            tx_query_task_greenlets = self.task_manager.running_greenlets.get(self.task_manager._maybe_query_evm_transactions, [])
            for greenlet in tx_query_task_greenlets:
                if greenlet.dead is False and greenlet.kwargs['address'] in addresses:
                    greenlet.kill(exception=GreenletKilledError('Killed due to request for evm address removal'))

    def reset_after_failed_account_creation_or_login(self) -> None:
        """If the account creation or login failed make sure that the rotki instance is clear

        Tricky instances are when after either failed premium credentials or user refusal
        to sync premium databases we relogged in
        """
        self.cryptocompare.db = None
        self.exchange_manager.delete_all_exchanges()
        self.data.logout()
        for instance in (self.cryptocompare, self.defillama, self.coingecko, self.alchemy, Inquirer()._manualcurrent):
            if instance.db is not None:  # unset DB if needed
                instance.unset_database()
        CachedSettings().reset()

    def _perform_new_db_actions(self) -> None:
        """Actions to perform at creation of a new DB"""
        # Using ORM for database operations
        with self.data.db.repos.unit_of_work():
            populate_rpc_nodes_in_database_orm(
                db=self.data.db,
            )

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

        self.data_importer = CSVDataImporter(db=self.data.db)
        self.premium_sync_manager = PremiumSyncManager(
            migration_manager=self.migration_manager,
            data=self.data,
        )
        # Set the DB in the instances that need it
        # TODO: These still need to be updated to use ORM
        self.cryptocompare.set_database(self.data.db)
        self.defillama.set_database(self.data.db)
        self.coingecko.set_database(self.data.db)
        self.alchemy.set_database(self.data.db)
        Inquirer()._manualcurrent.set_database(database=self.data.db)

        # Anything that was set above here has to be cleaned in case of failure in the next step
        # by reset_after_failed_account_creation_or_login()
        try:
            self.premium = self.premium_sync_manager.try_premium_at_start(
                given_premium_credentials=premium_credentials,
                username=user,
                create_new=create_new,
                sync_approval=sync_approval,
                sync_database=sync_database,
            )
        except PremiumAuthenticationError as e:
            # Reraise it only if this is during the creation of a new account where
            # the premium credentials were given by the user
            if create_new:
                raise
            self.msg_aggregator.add_warning(
                'Could not authenticate the rotki premium API keys found in the DB. '
                f'Error: {e}. Check logs for more details',
            )
            # else let's just continue. User signed in successfully, but he just
            # has unauthenticable/invalid premium credentials remaining in his DB

        # Get settings using ORM
        settings = self.get_settings()
        CachedSettings().initialize(settings)  # initialize with saved DB settings
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='submit_usage_analytics',
            exception_is_error=False,
            method=maybe_submit_usage_analytics,
            data_dir=self.data_dir,
            should_submit=settings.submit_usage_analytics,
        )
        self.beaconchain = BeaconChain(database=self.data.db, msg_aggregator=self.msg_aggregator)

        # Get exchange credentials using ORM
        exchange_credentials = self._get_exchange_credentials_orm()
        self.exchange_manager.initialize_exchanges(
            exchange_credentials=exchange_credentials,
        )
        self.exchange_manager.set_database(self.data.db)

        # Get blockchain accounts using ORM
        blockchain_accounts = self._get_blockchain_accounts_orm()

        etherscan = Etherscan(
            database=self.data.db,
            msg_aggregator=self.data.db.msg_aggregator,
        )

        # Initialize blockchain querying modules
        self.chains_aggregator = ChainsAggregator(
            blockchain_accounts=blockchain_accounts,
            ethereum_manager=EthereumManager(
                node_inquirer=(ethereum_inquirer := EthereumInquirer(
                    greenlet_manager=self.greenlet_manager,
                    database=self.data.db,
                    etherscan=etherscan,
                )),
                beacon_chain=self.beaconchain,
            ),
            optimism_manager=OptimismManager(OptimismInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            polygon_pos_manager=PolygonPOSManager(PolygonPOSInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            arbitrum_one_manager=ArbitrumOneManager(ArbitrumOneInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            base_manager=BaseManager(BaseInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            gnosis_manager=GnosisManager(GnosisInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            scroll_manager=ScrollManager(ScrollInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            binance_sc_manager=BinanceSCManager(BinanceSCInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            kusama_manager=SubstrateManager(
                chain=SupportedBlockchain.KUSAMA,
                msg_aggregator=self.msg_aggregator,
                greenlet_manager=self.greenlet_manager,
                connect_at_start=KUSAMA_NODES_TO_CONNECT_AT_START,
                connect_on_startup=len(blockchain_accounts.ksm) != 0,
                own_rpc_endpoint=settings.ksm_rpc_endpoint,
            ),
            polkadot_manager=SubstrateManager(
                chain=SupportedBlockchain.POLKADOT,
                msg_aggregator=self.msg_aggregator,
                greenlet_manager=self.greenlet_manager,
                connect_at_start=POLKADOT_NODES_TO_CONNECT_AT_START,
                connect_on_startup=len(blockchain_accounts.dot) != 0,
                own_rpc_endpoint=settings.dot_rpc_endpoint,
            ),
            avalanche_manager=AvalancheManager(
                avaxrpc_endpoint='https://api.avax.network/ext/bc/C/rpc',
                msg_aggregator=self.msg_aggregator,
            ),
            zksync_lite_manager=ZksyncLiteManager(
                ethereum_inquirer=ethereum_inquirer,
                database=self.data.db,
            ),
            msg_aggregator=self.msg_aggregator,
            database=self.data.db,
            greenlet_manager=self.greenlet_manager,
            premium=self.premium,
            eth_modules=settings.active_modules,
            data_directory=self.data_dir,
            beaconchain=self.beaconchain,
            btc_derivation_gap_limit=settings.btc_derivation_gap_limit,
        )
        Inquirer().inject_evm_managers([
            (chain.to_chain_id(), self.chains_aggregator.get_chain_manager(chain))
            for chain in EVM_CHAINS_WITH_TRANSACTIONS
        ])

        price_historian = PriceHistorian(  # Initialize the price historian singleton
            data_directory=self.data_dir,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=self.alchemy,
            uniswapv2=(uniswap_v2_oracle := UniswapV2Oracle()),
            uniswapv3=(uniswap_v3_oracle := UniswapV3Oracle()),
        )
        price_historian.set_oracles_order(settings.historical_price_oracles)

        Inquirer().add_defi_oracles(
            uniswap_v2=uniswap_v2_oracle,
            uniswap_v3=uniswap_v3_oracle,
        )
        Inquirer().set_oracles_order(settings.current_price_oracles)

        self.accountant = Accountant(
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            chains_aggregator=self.chains_aggregator,
            premium=self.premium,
        )
        self.history_querying_manager = HistoryQueryingManager(
            user_directory=self.user_directory,
            db=self.data.db,
            msg_aggregator=self.msg_aggregator,
            exchange_manager=self.exchange_manager,
            chains_aggregator=self.chains_aggregator,
        )
        self.data_updater = RotkiDataUpdater(
            msg_aggregator=self.msg_aggregator,
            user_db=self.data.db,
        )
        self.task_manager = TaskManager(
            max_tasks_num=DEFAULT_MAX_TASKS_NUM,
            greenlet_manager=self.greenlet_manager,
            api_task_greenlets=self.api_task_greenlets,
            database=self.data.db,
            chains_aggregator=self.chains_aggregator,
            exchange_manager=self.exchange_manager,
            cryptocompare=self.cryptocompare,
            data_updater=self.data_updater,
            premium_sync_manager=self.premium_sync_manager,
            eth_modules=settings.active_modules,
        )
        self.assets_updater = AssetsUpdater(
            msg_aggregator=self.msg_aggregator,
            coin_gecko_mappings_finisher=AssetWithOracles.finish_mappings,
        )
        self.user_is_logged_in = True
        log.debug('User unlocked')

    def _get_exchange_credentials_orm(self) -> dict[Location, list[Any]]:
        """Get exchange credentials using ORM"""
        db = self.data.db
        credentials_dict = defaultdict(list)

        all_credentials = db.repos.credentials.get_all_credentials()
        for cred in all_credentials:
            location = Location.deserialize_from_db(cred.location)
            # TODO: Build proper ExchangeApiCredentials object
            # TODO: This needs more complete implementation
            credentials_dict[location].append({
                'name': cred.name,
                'api_key': cred.api_key,
                'api_secret': cred.api_secret,
                'passphrase': cred.passphrase,
                'kraken_account_type': cred.kraken_account_type,
            })

        return dict(credentials_dict)

    def _get_blockchain_accounts_orm(self) -> ListOfBlockchainAddresses:
        """Get blockchain accounts using ORM"""
        db = self.data.db
        accounts = ListOfBlockchainAddresses()

        all_accounts = db.repos.accounts.get_all_accounts()

        # Group by blockchain
        for account in all_accounts:
            blockchain = SupportedBlockchain.deserialize(account.blockchain)
            address = account.account

            # Add to appropriate list based on blockchain
            if blockchain == SupportedBlockchain.BITCOIN:
                accounts.btc.append(BTCAddress(address))
            elif blockchain == SupportedBlockchain.BITCOIN_CASH:
                accounts.bch.append(BTCAddress(address))
            elif blockchain == SupportedBlockchain.ETHEREUM:
                accounts.eth.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.OPTIMISM:
                accounts.optimism.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.POLYGON_POS:
                accounts.polygon_pos.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.ARBITRUM_ONE:
                accounts.arbitrum_one.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.BASE:
                accounts.base.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.GNOSIS:
                accounts.gnosis.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.SCROLL:
                accounts.scroll.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.ZKSYNC_LITE:
                accounts.zksync_lite.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.AVALANCHE:
                accounts.avax.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.POLKADOT:
                accounts.dot.append(SubstrateAddress(address))
            elif blockchain == SupportedBlockchain.KUSAMA:
                accounts.ksm.append(SubstrateAddress(address))

        return accounts

    def get_settings(self, cursor: Any | None = None) -> DBSettings:
        """Get application settings using ORM

        Note: cursor parameter kept for backward compatibility but not used
        """
        # Get all settings from the repository
        settings_dict = self.data.db.repos.settings.get_all_settings()

        # Convert to DBSettings object
        # TODO: This conversion needs to be implemented properly
        # TODO: based on the actual DBSettings structure
        return DBSettings(**settings_dict)

    def logout(self) -> None:
        """Logout the current user"""
        if not self.user_is_logged_in:
            return

        user = self.data.username
        log.info('Logging out user', user=user)

        del self.chains_aggregator

        self.greenlet_manager.clear()
        self.shutdown_event.set()
        for greenlet in self.api_task_greenlets:
            greenlet.kill()
        if self.task_manager is not None:
            self.task_manager.shutdown()

        self.exchange_manager.delete_all_exchanges()
        self.data.logout()

        # Reset singleton instances
        for instance in (
                self.cryptocompare,
                self.defillama,
                self.coingecko,
                self.alchemy,
                Inquirer()._manualcurrent,
        ):
            if hasattr(instance, 'unset_database'):
                instance.unset_database()

        CachedSettings().reset()
        self.user_is_logged_in = False
        self.shutdown_event.clear()

        log.info('User successfully logged out', user=user)

    def set_settings(self, settings: ModifiableDBSettings) -> None:
        """Set new settings using ORM"""
        self.data.db.repos.settings.set_settings(settings)
        CachedSettings().initialize(settings)

    def get_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_types: list[str] | None = None,
    ) -> list[Any]:
        """Get history events using ORM"""
        return self.data.db.repos.history_events.get_events(
            from_timestamp=start_ts,
            to_timestamp=end_ts,
            event_types=event_types,
        )

    def add_history_event(self, event: Any) -> None:
        """Add a history event using ORM"""
        with self.data.db.repos.unit_of_work():
            self.data.db.repos.history_events.add_event(event)

    def get_ignored_assets(self) -> list[Asset]:
        """Get ignored assets using ORM"""
        ignored_assets = self.data.db.repos.ignored_assets.get_all_ignored_assets()
        return [Asset(asset.identifier) for asset in ignored_assets]

    def add_ignored_assets(self, assets: list[Asset]) -> None:
        """Add ignored assets using ORM"""
        with self.data.db.repos.unit_of_work():
            for asset in assets:
                self.data.db.repos.ignored_assets.add_ignored_asset(asset.identifier)

    def remove_ignored_assets(self, assets: list[Asset]) -> None:
        """Remove ignored assets using ORM"""
        with self.data.db.repos.unit_of_work():
            for asset in assets:
                self.data.db.repos.ignored_assets.remove_ignored_asset(asset.identifier)

    # Additional methods would be implemented following similar patterns
    # converting from DBHandler calls to ORM repository calls
