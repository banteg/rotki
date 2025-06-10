"""Blockchain-related scheduled tasks"""

from collections import defaultdict
from collections.abc import Callable
import logging
from typing import Optional

import gevent

from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.ethereum.modules.makerdao.cache import (
    query_ilk_registry_and_maybe_update_cache,
)
from rotkehlchen.chain.ethereum.modules.yearn.utils import query_yearn_vaults
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CHAIN_ID_TO_BOOSTER_ADDRESSES
from rotkehlchen.chain.evm.decoding.aura_finance.utils import query_aura_pools
from rotkehlchen.chain.evm.decoding.morpho.utils import (
    query_morpho_reward_distributors,
    query_morpho_vaults,
)
from rotkehlchen.chain.evm.decoding.pendle.constants import (
    PENDLE_SUPPORTED_CHAINS_WITHOUT_ETHEREUM,
)
from rotkehlchen.chain.evm.decoding.pendle.utils import query_pendle_yield_tokens
from rotkehlchen.constants import WEEK_IN_SECONDS
from rotkehlchen.constants.timing import (
    AAVE_V3_ASSETS_UPDATE,
    EVMLIKE_ACCOUNTS_DETECTION_REFRESH,
    HOUR_IN_SECONDS,
    OWNED_ASSETS_UPDATE,
    SPAM_ASSETS_DETECTION_REFRESH,
)
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.externalapis.gnosispay import init_gnosis_pay
from rotkehlchen.externalapis.monerium import init_monerium
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.tasks.assets import (
    autodetect_spam_assets_in_db,
    update_aave_v3_underlying_assets,
    update_owned_assets,
    update_spark_underlying_assets,
)
from rotkehlchen.tasks.utils import should_run_periodic_task
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    SUPPORTED_BITCOIN_CHAINS,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    Optional,
    SupportedBlockchain,
    Timestamp,
    get_args,
)
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

XPUB_DERIVATION_FREQUENCY = 3600
EVM_TX_QUERY_FREQUENCY = 3600
TX_RECEIPTS_QUERY_LIMIT = 500
TX_DECODING_LIMIT = 500


class BlockchainTasks:
    """Group blockchain related background tasks"""

    def __init__(
        self,
        greenlet_manager: 'GreenletManager',
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        query_yearn_vaults: Callable,
        query_morpho_vaults: Callable,
        query_pendle_yield_tokens: Callable,
        query_morpho_reward_distributors: Callable,
        query_aura_pools: Callable,
    ) -> None:
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.chains_aggregator = chains_aggregator
        self.query_yearn_vaults = query_yearn_vaults
        self.query_morpho_vaults = query_morpho_vaults
        self.query_pendle_yield_tokens = query_pendle_yield_tokens
        self.query_morpho_reward_distributors = query_morpho_reward_distributors
        self.query_aura_pools = query_aura_pools
        self.last_xpub_derivation_ts = 0
        self.last_evm_tx_query_ts: defaultdict[tuple[ChecksumEvmAddress, SupportedBlockchain], int] = defaultdict(int)

    def maybe_schedule_xpub_derivation(self) -> Optional[list[gevent.Greenlet]]:
        now = ts_now()
        if now - self.last_xpub_derivation_ts <= XPUB_DERIVATION_FREQUENCY:
            return None
        with self.database.conn.read_ctx() as cursor:
            btc_xpubs = self.database.get_bitcoin_xpub_data(cursor, SupportedBlockchain.BITCOIN)
            bch_xpubs = self.database.get_bitcoin_xpub_data(cursor, SupportedBlockchain.BITCOIN_CASH)
        should_derive_xpubs = {
            SupportedBlockchain.BITCOIN: len(btc_xpubs) > 0,
            SupportedBlockchain.BITCOIN_CASH: len(bch_xpubs) > 0,
        }
        if not any(should_derive_xpubs.values()):
            return None
        greenlets = []
        self.last_xpub_derivation_ts = now
        xpub_manager = XpubManager(chains_aggregator=self.chains_aggregator)
        for chain in get_args(SUPPORTED_BITCOIN_CHAINS):
            if not should_derive_xpubs[chain]:
                continue
            log.debug(f'Scheduling task for {chain} Xpub derivation')
            greenlets.append(
                self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name=f'Derive new xpub addresses for {chain}',
                    exception_is_error=True,
                    method=xpub_manager.check_for_new_xpub_addresses,
                    blockchain=chain,
                )
            )
        return greenlets

    def maybe_query_evm_transactions(self) -> Optional[list[gevent.Greenlet]]:
        shuffled_chains = list(EVM_CHAINS_WITH_TRANSACTIONS)
        random.shuffle(shuffled_chains)
        for blockchain in shuffled_chains:
            with self.database.conn.read_ctx() as cursor:
                accounts = self.database.get_blockchain_accounts(cursor).get(blockchain)
                if len(accounts) == 0:
                    continue
                now = ts_now()
                dbevmtx = DBEvmTx(self.database)
                queriable_accounts: list[ChecksumEvmAddress] = []
                for account in accounts:
                    _, end_ts = dbevmtx.get_queried_range(cursor, account, blockchain)
                    if now - max(self.last_evm_tx_query_ts[account, blockchain], end_ts) > EVM_TX_QUERY_FREQUENCY:
                        queriable_accounts.append(account)
            if len(queriable_accounts) == 0:
                continue
            evm_manager = self.chains_aggregator.get_chain_manager(blockchain)
            address = random.choice(queriable_accounts)
            task_name = f'Query {blockchain!s} transactions for {address}'
            log.debug(f'Scheduling task to {task_name}')
            self.last_evm_tx_query_ts[address, blockchain] = now
            return [
                self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name=task_name,
                    exception_is_error=True,
                    method=evm_manager.transactions.single_address_query_transactions,
                    address=address,
                    start_ts=0,
                    end_ts=now,
                )
            ]
        return None

    def maybe_schedule_evm_txreceipts(self) -> Optional[list[gevent.Greenlet]]:
        dbevmtx = DBEvmTx(self.database)
        shuffled_chains = list(EVM_CHAINS_WITH_TRANSACTIONS)
        random.shuffle(shuffled_chains)
        for blockchain in shuffled_chains:
            hash_results = dbevmtx.get_transaction_hashes_no_receipt(
                tx_filter_query=EvmTransactionsFilterQuery.make(chain_id=blockchain.to_chain_id()),
                limit=TX_RECEIPTS_QUERY_LIMIT,
            )
            if len(hash_results) == 0:
                return None
            evm_inquirer = self.chains_aggregator.get_chain_manager(blockchain)
            task_name = f'Query {len(hash_results)} {blockchain!s} transactions receipts'
            log.debug(f'Scheduling task to {task_name}')
            return [
                self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name=task_name,
                    exception_is_error=True,
                    method=evm_inquirer.transactions.get_receipts_for_transactions_missing_them,
                    limit=TX_RECEIPTS_QUERY_LIMIT,
                )
            ]
        return None

    def maybe_decode_evm_transactions(self) -> Optional[list[gevent.Greenlet]]:
        dbevmtx = DBEvmTx(self.database)
        shuffled_chains = list(EVM_CHAINS_WITH_TRANSACTIONS)
        random.shuffle(shuffled_chains)
        for blockchain in shuffled_chains:
            number_of_tx_to_decode = dbevmtx.count_hashes_not_decoded(chain_id=blockchain.to_chain_id())
            if number_of_tx_to_decode == 0:
                return None
            evm_inquirer = self.chains_aggregator.get_chain_manager(blockchain)
            task_name = f'decode {min(number_of_tx_to_decode, TX_DECODING_LIMIT)} {blockchain!s} transactions'
            log.debug(f'Scheduling periodic task to {task_name}')
            return [
                self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name=task_name,
                    exception_is_error=True,
                    method=evm_inquirer.transactions_decoder.get_and_decode_undecoded_transactions,
                    limit=TX_DECODING_LIMIT,
                )
            ]
        return None

    def maybe_query_produced_blocks(self) -> Optional[list[gevent.Greenlet]]:
        if (
            self.chains_aggregator.get_module('eth2') is None or
            self.chains_aggregator.beaconchain.is_rate_limited() or
            self.chains_aggregator.beaconchain.produced_blocks_lock.locked() or
            len(indices := self.chains_aggregator.beaconchain.get_outdated_validators_to_query_for_blocks()) == 0
        ):
            return None
        task_name = 'Periodically query produced blocks'
        log.debug(f'Scheduling task to {task_name}')
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=self.chains_aggregator.beaconchain.get_and_store_produced_blocks,
                indices=indices,
            )
        ]

    def maybe_query_withdrawals(self) -> Optional[list[gevent.Greenlet]]:
        if (eth2 := self.chains_aggregator.get_module('eth2')) is None:
            return None
        if eth2.withdrawals_query_lock.locked():
            return None
        now = ts_now()
        with self.database.conn.read_ctx() as cursor:
            key_name = DBCacheDynamic.WITHDRAWALS_TS.value[0][:17]
            cursor.execute(
                'SELECT DISTINCT ev.withdrawal_address FROM eth2_validators ev '
                f"LEFT JOIN key_value_cache kv ON kv.name = '{key_name}' || ev.withdrawal_address "
                'WHERE kv.value <= ? OR kv.name IS NULL',
                (ts_now() - HOUR_IN_SECONDS * 3,),
            )
            if len(addresses := [row[0] for row in cursor]) == 0:
                return None
        task_name = 'Periodically query ethereum withdrawals'
        log.debug(f'Scheduling task to {task_name}')
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=eth2.query_services_for_validator_withdrawals,
                addresses=addresses,
                to_ts=now,
            )
        ]

    def maybe_detect_withdrawal_exits(self) -> Optional[list[gevent.Greenlet]]:
        if (eth2 := self.chains_aggregator.get_module('eth2')) is None:
            return None
        with self.database.conn.read_ctx() as cursor:
            result = self.database.get_static_cache(cursor=cursor, name=DBCacheStatic.LAST_WITHDRAWALS_EXIT_QUERY_TS)
            if result is not None and ts_now() - result <= HOUR_IN_SECONDS * 2:
                return None
        task_name = 'Periodically detect withdrawal exits'
        log.debug(f'Scheduling task to {task_name}')
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=eth2.detect_exited_validators,
            )
        ]

    def maybe_run_events_processing(self) -> Optional[list[gevent.Greenlet]]:
        now = ts_now()
        with self.database.conn.read_ctx() as cursor:
            result = self.database.get_static_cache(cursor=cursor, name=DBCacheStatic.LAST_EVENTS_PROCESSING_TASK_TS)
            if result is not None and now - result <= HOUR_IN_SECONDS:
                return None
        task_name = 'Periodically process events'
        log.debug(f'Scheduling task to {task_name}')
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=process_events,
                chains_aggregator=self.chains_aggregator,
                database=self.database,
            )
        ]

    def maybe_update_yearn_vaults(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            if len(self.database.get_single_blockchain_addresses(cursor, SupportedBlockchain.ETHEREUM)) == 0:
                return None
        if should_update_protocol_cache(self.database, CacheType.YEARN_VAULTS) is True:
            return [
                self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name='Update yearn vaults',
                    exception_is_error=False,
                    method=self.query_yearn_vaults,
                    db=self.database,
                    ethereum_inquirer=self.chains_aggregator.ethereum.node_inquirer,
                )
            ]
        return None

    def maybe_update_morpho_cache(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            account_data = self.database.get_blockchain_accounts(cursor)
            if (
                len(account_data.get(SupportedBlockchain.ETHEREUM)) == 0 and
                len(account_data.get(SupportedBlockchain.BASE)) == 0
            ):
                return None
        greenlets = []
        if should_update_protocol_cache(self.database, CacheType.MORPHO_VAULTS) is True:
            greenlets.append(
                self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name='Update Morpho vaults',
                    exception_is_error=False,
                    method=self.query_morpho_vaults,
                    database=self.database,
                )
            )
        if any(
            should_update_protocol_cache(
                userdb=self.database,
                cache_key=CacheType.MORPHO_REWARD_DISTRIBUTORS,
                args=(str(chain_id),),
            )
            for chain_id in {ChainID.ETHEREUM, ChainID.BASE}
        ):
            greenlets.append(
                self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name='Update Morpho reward distributors',
                    exception_is_error=False,
                    method=self.query_morpho_reward_distributors,
                )
            )
        return greenlets if len(greenlets) > 0 else None

    def maybe_update_pendle_cache(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            account_data = self.database.get_blockchain_accounts(cursor)
            if (
                len(account_data.get(SupportedBlockchain.ARBITRUM_ONE)) == 0 and
                len(account_data.get(SupportedBlockchain.ETHEREUM)) == 0 and
                len(account_data.get(SupportedBlockchain.BASE)) == 0 and
                len(account_data.get(SupportedBlockchain.BINANCE_SC)) == 0 and
                len(account_data.get(SupportedBlockchain.OPTIMISM)) == 0
            ):
                return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'Update Pendle yield tokens for {chain.to_name()}',
                exception_is_error=False,
                method=self.query_pendle_yield_tokens,
                evm_inquirer=self.chains_aggregator.get_evm_manager(chain).node_inquirer,
            )
            for chain in PENDLE_SUPPORTED_CHAINS_WITHOUT_ETHEREUM | {ChainID.ETHEREUM}
            if should_update_protocol_cache(self.database, CacheType.PENDLE_YIELD_TOKENS, (str(chain.serialize()),)) is True
        ]

    def maybe_update_aura_pools(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            account_data = self.database.get_blockchain_accounts(cursor)
            if (
                len(account_data.get(SupportedBlockchain.ETHEREUM)) == 0 and
                len(account_data.get(SupportedBlockchain.BASE)) == 0 and
                len(account_data.get(SupportedBlockchain.OPTIMISM)) == 0 and
                len(account_data.get(SupportedBlockchain.POLYGON_POS)) == 0 and
                len(account_data.get(SupportedBlockchain.ARBITRUM_ONE)) == 0 and
                len(account_data.get(SupportedBlockchain.GNOSIS)) == 0
            ):
                return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'Update Aura pools for {chain.to_name()}',
                exception_is_error=False,
                method=self.query_aura_pools,
                evm_inquirer=self.chains_aggregator.get_evm_manager(chain).node_inquirer,
            )
            for chain in CHAIN_ID_TO_BOOSTER_ADDRESSES
            if should_update_protocol_cache(self.database, CacheType.AURA_POOLS, (str(chain.value),)) is True
        ]

    def maybe_detect_evm_accounts(self) -> Optional[list[gevent.Greenlet]]:
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS, EVMLIKE_ACCOUNTS_DETECTION_REFRESH) is False:
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Detect EVM accounts',
                exception_is_error=True,
                method=self.chains_aggregator.detect_evm_accounts,
                progress_handler=None,
                chains=self.database.get_chains_to_detect_evm_accounts(),
            )
        ]

    def maybe_update_ilk_cache(self) -> Optional[list[gevent.Greenlet]]:
        with self.database.conn.read_ctx() as cursor:
            if len(self.database.get_single_blockchain_addresses(cursor, SupportedBlockchain.ETHEREUM)) == 0:
                return None
        if should_update_protocol_cache(self.database, CacheType.MAKERDAO_VAULT_ILK, 'ETH-A') is True:
            return [
                self.greenlet_manager.spawn_and_track(
                    after_seconds=None,
                    task_name='Update ilk cache',
                    exception_is_error=True,
                    method=query_ilk_registry_and_maybe_update_cache,
                    ethereum=self.chains_aggregator.ethereum.node_inquirer,
                )
            ]
        return None

    def maybe_detect_new_spam_tokens(self) -> Optional[list[gevent.Greenlet]]:
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY, SPAM_ASSETS_DETECTION_REFRESH) is False:
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Detect spam assets in globaldb',
                exception_is_error=True,
                method=autodetect_spam_assets_in_db,
                user_db=self.database,
            )
        ]

    def maybe_update_owned_assets(self) -> Optional[list[gevent.Greenlet]]:
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_OWNED_ASSETS_UPDATE, OWNED_ASSETS_UPDATE) is False:
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update owned assets in globaldb',
                exception_is_error=True,
                method=update_owned_assets,
                user_db=self.database,
            )
        ]

    def maybe_update_aave_v3_underlying_assets(self) -> Optional[list[gevent.Greenlet]]:
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_AAVE_V3_ASSETS_UPDATE, AAVE_V3_ASSETS_UPDATE) is False:
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update aave v3 underlying assets in globaldb',
                exception_is_error=True,
                method=update_aave_v3_underlying_assets,
                chains_aggregator=self.chains_aggregator,
            )
        ]

    def maybe_update_spark_underlying_assets(self) -> Optional[list[gevent.Greenlet]]:
        if should_run_periodic_task(
            database=self.database,
            refresh_period=WEEK_IN_SECONDS,
            key_name=DBCacheStatic.LAST_SPARK_ASSETS_UPDATE,
        ) is False:
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Update Spark underlying assets in globaldb',
                exception_is_error=True,
                method=update_spark_underlying_assets,
                chains_aggregator=self.chains_aggregator,
            )
        ]

    def maybe_query_monerium(self) -> Optional[list[gevent.Greenlet]]:
        if not has_premium_check(self.chains_aggregator.premium):
            return None
        if (monerium := init_monerium(self.database)) is None:
            return None
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_MONERIUM_QUERY_TS, HOUR_IN_SECONDS) is False:
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Query monerium',
                exception_is_error=False,
                method=monerium.get_and_process_orders,
            )
        ]

    def maybe_query_gnosispay(self) -> Optional[list[gevent.Greenlet]]:
        if not has_premium_check(self.chains_aggregator.premium):
            return None
        if (gnosispay := init_gnosis_pay(self.database)) is None:
            return None
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_GNOSISPAY_QUERY_TS, HOUR_IN_SECONDS) is False:
            return None
        from_ts = Timestamp(0)
        with self.database.conn.read_ctx() as cursor:
            cursor.execute('SELECT value FROM key_value_cache WHERE name=?', (DBCacheStatic.LAST_GNOSISPAY_QUERY_TS.value,))
            if (result := cursor.fetchone()) is not None:
                from_ts = deserialize_timestamp(result[0])
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Query Gnosis Pay transaction',
                exception_is_error=False,
                method=gnosispay.get_and_process_transactions,
                after_ts=from_ts,
            )
        ]

    def maybe_query_graph_delegated_tokens(self) -> Optional[list[gevent.Greenlet]]:
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS, DAY_IN_SECONDS) is False:
            return None
        if len(self.chains_aggregator.accounts.get(SupportedBlockchain.ETHEREUM)) == 0:
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name="Search for Graph's GRT DelegationTransferredToL2 events",
                exception_is_error=True,
                method=self.chains_aggregator.ethereum.transactions.query_for_graph_delegation_txns,
                addresses=self.chains_aggregator.accounts.eth,
            )
        ]
