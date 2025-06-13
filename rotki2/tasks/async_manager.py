"""Async Task Manager for rotki2 using anyio.

This replaces the gevent-based TaskManager from rotkehlchen with a modern
async implementation using anyio task groups.
"""
import logging
import random
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple

import anyio
from anyio import CancelScope

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.constants import WEEK_IN_SECONDS
from rotkehlchen.constants.timing import (
    AAVE_V3_ASSETS_UPDATE,
    DATA_UPDATES_REFRESH,
    DAY_IN_SECONDS,
    EVMLIKE_ACCOUNTS_DETECTION_REFRESH,
    HOUR_IN_SECONDS,
    OWNED_ASSETS_UPDATE,
    SPAM_ASSETS_DETECTION_REFRESH,
)
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.calendar import CalendarEntry
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, has_premium_check, premium_create_and_verify
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    SUPPORTED_BITCOIN_CHAINS,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    ExchangeLocationID,
    Location,
    Optional,
    SupportedBlockchain,
    Timestamp,
    get_args,
)
from rotkehlchen.utils.misc import ts_now
from rotki2.tasks.anyio_manager import AnyioTaskManager

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.updates import RotkiDataUpdater
    from rotkehlchen.exchanges.manager import ExchangeManager
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.premium.sync import PremiumSyncManager
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Task scheduling constants
CRYPTOCOMPARE_QUERY_AFTER_SECS = 86400  # a day
DEFAULT_MAX_TASKS_NUM = 2
CRYPTOCOMPARE_HISTOHOUR_FREQUENCY = 240  # at least 4 mins apart
XPUB_DERIVATION_FREQUENCY = 3600  # every hour
EVM_TX_QUERY_FREQUENCY = 3600  # every hour
EXCHANGE_QUERY_FREQUENCY = 3600  # every hour
PREMIUM_STATUS_CHECK = 3600  # every hour
TX_RECEIPTS_QUERY_LIMIT = 500
TX_DECODING_LIMIT = 500
PREMIUM_CHECK_RETRY_LIMIT = 3


class CCHistoQuery(NamedTuple):
    from_asset: AssetWithOracles
    to_asset: AssetWithOracles


class AsyncTaskManager:
    """Async replacement for the gevent-based TaskManager."""

    def __init__(
            self,
            max_tasks_num: int,
            task_manager: AnyioTaskManager,
            api_task_count: int,  # Count of API tasks (replaces api_task_greenlets)
            database: 'DBHandler',
            cryptocompare: 'Cryptocompare',
            premium_sync_manager: Optional['PremiumSyncManager'],
            chains_aggregator: 'ChainsAggregator',
            exchange_manager: 'ExchangeManager',
            deactivate_premium: Callable[[], None],
            activate_premium: Callable[[Premium], None],
            query_balances: Callable,
            msg_aggregator: 'MessagesAggregator',
            data_updater: 'RotkiDataUpdater',
            username: str,
    ) -> None:
        self.should_schedule = False
        self.max_tasks_num = max_tasks_num
        self.task_manager = task_manager
        self.api_task_count = api_task_count
        self.database = database
        self.cryptocompare = cryptocompare
        self.exchange_manager = exchange_manager
        self.cryptocompare_queries: set[CCHistoQuery] = set()
        self.chains_aggregator = chains_aggregator
        self.last_xpub_derivation_ts = 0
        self.last_evm_tx_query_ts: defaultdict[tuple[ChecksumEvmAddress, SupportedBlockchain], int] = defaultdict(int)
        self.last_exchange_query_ts: defaultdict[ExchangeLocationID, int] = defaultdict(int)
        self.prepared_cryptocompare_query = False
        self.running_tasks: dict[Callable, list[str]] = {}  # task_name -> list of task IDs
        self.deactivate_premium = deactivate_premium
        self.activate_premium = activate_premium
        self.query_balances = query_balances
        self.last_balance_query_ts = Timestamp(0)
        self.last_premium_status_check = ts_now()
        self.last_calendar_reminder_check = Timestamp(0)
        self.msg_aggregator = msg_aggregator
        self.premium_check_retries = 0
        self.premium_sync_manager: Optional[PremiumSyncManager] = premium_sync_manager
        self.data_updater = data_updater
        self.username = username

        # Schedule lock (asyncio-compatible)
        self.schedule_lock = anyio.Lock()
        self._scheduler_running = False
        self._scheduler_cancel_scope: CancelScope | None = None

        # Initialize potential tasks (async versions)
        self.potential_tasks: list[Callable[[], bool]] = [
            self._maybe_schedule_cryptocompare_query,
            self._maybe_schedule_xpub_derivation,
            self._maybe_query_evm_transactions,
            self._maybe_schedule_exchange_history_query,
            self._maybe_schedule_evm_txreceipts,
            self._maybe_decode_evm_transactions,
            self._maybe_check_premium_status,
            self._maybe_check_data_updates,
            self._maybe_update_snapshot_balances,
            self._maybe_update_yearn_vaults,
            self._maybe_update_morpho_cache,
            self._maybe_update_aura_pools,
            self._maybe_detect_evm_accounts,
            self._maybe_update_ilk_cache,
            self._maybe_query_produced_blocks,
            self._maybe_query_withdrawals,
            self._maybe_run_events_processing,
            self._maybe_detect_withdrawal_exits,
            self._maybe_detect_new_spam_tokens,
            self._maybe_query_monerium,
            self._maybe_update_owned_assets,
            self._maybe_update_aave_v3_underlying_assets,
            self._maybe_update_spark_underlying_assets,
            self._maybe_create_calendar_reminder,
            self._maybe_trigger_calendar_reminder,
            self._maybe_delete_past_calendar_events,
            self._maybe_query_graph_delegated_tokens,
            self._maybe_query_gnosispay,
            self._maybe_update_pendle_cache,
        ]
        if self.premium_sync_manager is not None:
            self.potential_tasks.append(self._maybe_schedule_db_upload)

    async def start_scheduling(self) -> None:
        """Start the task scheduler loop."""
        if self._scheduler_running:
            return

        self._scheduler_running = True
        log.debug('Starting async task scheduler')
        
        async def scheduler_loop() -> None:
            while self._scheduler_running:
                try:
                    await self.schedule()
                    # Schedule tasks every 60 seconds
                    await anyio.sleep(60)
                except Exception as e:
                    log.error(f'Error in scheduler loop: {e}')
                    await anyio.sleep(60)  # Continue after error

        with anyio.CancelScope() as cancel_scope:
            self._scheduler_cancel_scope = cancel_scope
            await scheduler_loop()

    async def stop_scheduling(self) -> None:
        """Stop the task scheduler and cancel all tasks."""
        self._scheduler_running = False
        if self._scheduler_cancel_scope:
            self._scheduler_cancel_scope.cancel()
        await self.clear()

    async def _prepare_cryptocompare_queries(self) -> None:
        """Prepare the queries to do to cryptocompare.
        
        Runs only once and then has a number of queries prepared for the task manager to schedule.
        """
        log.debug('Preparing cryptocompare historical price queries')
        if len(self.cryptocompare_queries) != 0:
            return

        with self.database.conn.read_ctx() as cursor:
            assets = self.database.query_owned_assets(cursor)
            main_currency = self.database.get_setting(cursor=cursor, name='main_currency')

        if main_currency.cryptocompare == '':  # main currency not supported
            self.prepared_cryptocompare_query = True
            return

        now_ts = ts_now()
        for raw_asset in assets:
            try:
                asset = raw_asset.resolve_to_asset_with_oracles()
            except (UnknownAsset, WrongAssetType):
                continue  # cryptocompare does not work with non-oracles assets

            if asset.is_fiat() and main_currency.is_fiat():
                continue  # ignore fiat to fiat

            if asset.cryptocompare == '':
                continue  # not supported in cryptocompare

            if asset.cryptocompare is None and asset.symbol is None:
                continue  # type: ignore  # asset.symbol may be None for auto generated underlying tokens

            data_range = GlobalDBHandler.get_historical_price_range(
                from_asset=asset,
                to_asset=main_currency,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
            )
            if data_range is not None and now_ts - data_range[1] < CRYPTOCOMPARE_QUERY_AFTER_SECS:
                continue

            self.cryptocompare_queries.add(CCHistoQuery(from_asset=asset, to_asset=main_currency))

        self.prepared_cryptocompare_query = True

    async def _maybe_schedule_cryptocompare_query(self) -> bool:
        """Schedule a cryptocompare query for a single asset history."""
        if self.prepared_cryptocompare_query is False:
            await self._prepare_cryptocompare_queries()

        if len(self.cryptocompare_queries) == 0:
            return False

        # If there is already a cryptocompare query running don't schedule another
        if self.task_manager.has_task('Cryptocompare historical prices'):
            return False

        now_ts = ts_now()
        # Make sure there is a long enough period between an asset's histohour query
        # to avoid getting rate limited by cryptocompare
        if now_ts - self.cryptocompare.last_histohour_query_ts <= CRYPTOCOMPARE_HISTOHOUR_FREQUENCY:
            return False

        query = self.cryptocompare_queries.pop()
        task_name = f'Cryptocompare historical prices {query.from_asset} / {query.to_asset} query'
        log.debug(f'Scheduling task for {task_name}')
        
        await self.task_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=False,
            method=self.cryptocompare.query_and_store_historical_data,
            from_asset=query.from_asset,
            to_asset=query.to_asset,
            timestamp=now_ts,
        )
        return True

    # Placeholder implementations for all the task scheduling methods
    # These would need full implementation with proper async conversions

    async def _maybe_schedule_xpub_derivation(self) -> bool:
        """Schedule the xpub derivation task if enough time has passed."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_query_evm_transactions(self) -> bool:
        """Schedule the evm transaction query task if enough time has passed."""
        shuffled_chains = list(EVM_CHAINS_WITH_TRANSACTIONS)
        random.shuffle(shuffled_chains)
        
        for blockchain in shuffled_chains:
            with self.database.conn.read_ctx() as cursor:
                accounts = self.database.get_blockchain_accounts(cursor).get(blockchain)
                if not accounts or len(accounts) == 0:
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
            
            # Since this task is heavy we spawn it only for one chain at a time.
            await self.task_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=evm_manager.transactions.single_address_query_transactions,
                address=address,
                start_ts=0,
                end_ts=now,
            )
            return True
        return False

    async def _maybe_schedule_exchange_history_query(self) -> bool:
        """Schedule the exchange history query task if enough time has passed."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_schedule_evm_txreceipts(self) -> bool:
        """Schedule the evm transaction receipts query task."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_decode_evm_transactions(self) -> bool:
        """Schedule the evm transaction decoding task."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_check_premium_status(self) -> bool:
        """Validate the premium status of the account."""
        now = ts_now()
        if now - self.last_premium_status_check < PREMIUM_STATUS_CHECK:
            return False

        log.debug('Running the premium status check')
        with self.database.conn.read_ctx() as cursor:
            db_credentials = self.database.get_rotkehlchen_premium(cursor)
        if db_credentials is None:
            self.last_premium_status_check = now
            return False

        try:
            premium = premium_create_and_verify(
                credentials=db_credentials,
                username=self.username,
            )
        except RemoteError:
            if self.premium_check_retries < PREMIUM_CHECK_RETRY_LIMIT:
                self.premium_check_retries += 1
                log.debug(
                    f'Premium check failed {self.premium_check_retries} times. Not '
                    f'sending deactivate message yet',
                )
                self.last_premium_status_check = now
                return False
            log.debug('Premium check failed due to remote error. Sending deactivate message')
            self.msg_aggregator.add_message(
                message_type=WSMessageType.PREMIUM_STATUS_UPDATE,
                data={
                    'is_premium_active': False,
                    'expired': False,
                },
            )
            self.deactivate_premium()
        except PremiumAuthenticationError:
            log.debug('Premium check failed due to authentication error. Sending deactivate message')
            self.deactivate_premium()
            self.msg_aggregator.add_message(
                message_type=WSMessageType.PREMIUM_STATUS_UPDATE,
                data={
                    'is_premium_active': False,
                    'expired': True,
                },
            )
        else:
            log.debug('Premium check successful. Sending activate message')
            self.activate_premium(premium)
            self.msg_aggregator.add_message(
                message_type=WSMessageType.PREMIUM_STATUS_UPDATE,
                data={
                    'is_premium_active': True,
                    'expired': False,
                },
            )
            self.premium_check_retries = 0
        finally:
            self.last_premium_status_check = now
        
        return True

    async def _maybe_check_data_updates(self) -> bool:
        """Schedule the data update task."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_update_snapshot_balances(self) -> bool:
        """Update the balances of a user if needed."""
        with self.database.conn.read_ctx() as read_cursor:
            if not self.database.should_save_balances(
                cursor=read_cursor,
                last_query_ts=self.last_balance_query_ts,
            ):
                return False

        # This would need to be converted to async
        # maybe_detect_new_tokens(self.database)
        task_name = 'Periodically update snapshot balances'
        log.debug(f'Scheduling task to {task_name}')
        
        await self.task_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=self.query_balances,  # This would need to be async
            requested_save_data=True,
            save_despite_errors=False,
            timestamp=None,
            ignore_cache=True,
        )
        return True

    async def _maybe_update_yearn_vaults(self) -> bool:
        """Update Yearn vaults cache."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_update_morpho_cache(self) -> bool:
        """Update Morpho protocol cache."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_update_aura_pools(self) -> bool:
        """Update Aura Finance pools cache."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_detect_evm_accounts(self) -> bool:
        """Schedule EVM accounts detection task."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_update_ilk_cache(self) -> bool:
        """Update MakerDAO ILK cache."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_query_produced_blocks(self) -> bool:
        """Schedule blocks production query."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_query_withdrawals(self) -> bool:
        """Schedule Ethereum withdrawal query."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_run_events_processing(self) -> bool:
        """Schedule events processing task."""
        now = ts_now()
        with self.database.conn.read_ctx() as cursor:
            result = self.database.get_static_cache(
                cursor=cursor, name=DBCacheStatic.LAST_EVENTS_PROCESSING_TASK_TS,
            )
            if result is not None and now - result <= HOUR_IN_SECONDS:
                return False

        task_name = 'Periodically process events'
        log.debug(f'Scheduling task to {task_name}')
        
        await self.task_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=self._process_events_async,
        )
        return True

    async def _process_events_async(self) -> None:
        """Async version of events processing."""
        # This would be converted from rotkehlchen/tasks/events.py
        eth2 = self.chains_aggregator.get_module('eth2')
        if eth2 is not None:
            # These methods would need to be converted to async
            eth2.combine_block_with_tx_events()
            eth2.refresh_activated_validators_deposits()

        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.LAST_EVENTS_PROCESSING_TASK_TS,
                value=ts_now(),
            )

    async def _maybe_detect_withdrawal_exits(self) -> bool:
        """Schedule withdrawal exits detection."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_detect_new_spam_tokens(self) -> bool:
        """Schedule spam token detection."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_query_monerium(self) -> bool:
        """Schedule Monerium query."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_update_owned_assets(self) -> bool:
        """Schedule owned assets update."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_update_aave_v3_underlying_assets(self) -> bool:
        """Schedule Aave V3 underlying assets update."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_update_spark_underlying_assets(self) -> bool:
        """Schedule Spark underlying assets update."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_create_calendar_reminder(self) -> bool:
        """Schedule calendar reminder creation."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_trigger_calendar_reminder(self) -> bool:
        """Schedule calendar reminder notifications."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_delete_past_calendar_events(self) -> bool:
        """Schedule deletion of past calendar events."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_query_graph_delegated_tokens(self) -> bool:
        """Schedule Graph delegation query."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_query_gnosispay(self) -> bool:
        """Schedule Gnosis Pay query."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_update_pendle_cache(self) -> bool:
        """Schedule Pendle cache update."""
        # Implementation would go here - convert from gevent version
        return False

    async def _maybe_schedule_db_upload(self) -> bool:
        """Schedule database upload to premium servers."""
        assert self.premium_sync_manager is not None, 'caller should make sure premium sync manager exists'
        if self.premium_sync_manager.check_if_should_sync(force_upload=False) is False:
            return False

        log.debug('Scheduling task for DB upload to server')
        await self.task_manager.spawn_and_track(
            after_seconds=None,
            task_name='Upload data to server',
            exception_is_error=True,
            method=self.premium_sync_manager.maybe_upload_data_to_server,
        )
        return True

    async def _schedule(self) -> None:
        """Schedule background tasks."""
        self.task_manager.clear_finished()
        # Also clear methods mapping in the task manager
        self.running_tasks = {
            method: task_ids
            for method, task_ids in self.running_tasks.items()
            if any(not self.task_manager.has_task(task_id) for task_id in task_ids)
        }
        
        current_tasks = len(self.task_manager.tasks) + self.api_task_count
        not_proceed = current_tasks >= self.max_tasks_num
        log.debug(
            f'At task scheduling. Current tasks: {current_tasks} '
            f'Max tasks: {self.max_tasks_num}. '
            f'{"Will not schedule" if not_proceed else "Will schedule"}.',
        )
        if not_proceed:
            return  # too busy

        random.shuffle(self.potential_tasks)
        max_tasks = min(self.max_tasks_num - current_tasks, len(self.potential_tasks))

        spawned_new = 0
        for scheduling_fn in self.potential_tasks:
            if spawned_new >= max_tasks:
                break  # no more task slots left
            if scheduling_fn in self.running_tasks:
                continue  # the specified task is already running
            
            scheduled = await scheduling_fn()
            if scheduled:
                spawned_new += 1

    async def schedule(self) -> None:
        """Schedule background task while holding the scheduling lock.
        
        Only if should_schedule has been set to True, which happens after the first
        time the user loads up the dashboard. This is to avoid any background tasks running
        during user migrations, db upgrades and asset upgrades.
        """
        if self.should_schedule is False:
            return

        async with self.schedule_lock:
            if self.should_schedule:  # double-check after acquiring lock
                await self._schedule()

    async def clear(self) -> None:
        """Ensure that no task is kept referenced. Used when removing the task manager."""
        await self.task_manager.clear()
        self.running_tasks.clear()
        self.should_schedule = False