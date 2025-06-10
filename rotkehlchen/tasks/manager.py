import logging
import random
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple

import gevent

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.constants import WEEK_IN_SECONDS
from rotkehlchen.constants.timing import DATA_UPDATES_REFRESH
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.api import PremiumAuthenticationError
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, has_premium_check, premium_create_and_verify
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.tasks.assets import maybe_detect_new_tokens
from rotkehlchen.types import Optional, Timestamp
from rotkehlchen.utils.misc import ts_now
from .blockchain import BlockchainTasks
from .exchange import ExchangeTasks
from .reminders import ReminderTasks

from .events import process_events

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.updates import RotkiDataUpdater
    from rotkehlchen.exchanges.manager import ExchangeManager
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.greenlets.manager import GreenletManager
    from rotkehlchen.premium.sync import PremiumSyncManager
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


CRYPTOCOMPARE_QUERY_AFTER_SECS = 86400  # a day
DEFAULT_MAX_TASKS_NUM = 2
CRYPTOCOMPARE_HISTOHOUR_FREQUENCY = 240  # at least 4 mins apart
PREMIUM_STATUS_CHECK = 3600  # every hour
PREMIUM_CHECK_RETRY_LIMIT = 3


def exchange_fail_cb(error: str) -> None:
    log.error(error)


class CCHistoQuery(NamedTuple):
    from_asset: AssetWithOracles
    to_asset: AssetWithOracles


class TaskManager:

    def __init__(
            self,
            max_tasks_num: int,
            greenlet_manager: 'GreenletManager',
            api_task_greenlets: list[gevent.Greenlet],
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
        self.greenlet_manager = greenlet_manager
        self.api_task_greenlets = api_task_greenlets
        self.database = database
        self.cryptocompare = cryptocompare
        self.exchange_manager = exchange_manager
        self.cryptocompare_queries: set[CCHistoQuery] = set()
        self.chains_aggregator = chains_aggregator
        self.blockchain_tasks = BlockchainTasks(
            greenlet_manager=greenlet_manager,
            database=database,
            chains_aggregator=chains_aggregator,
            query_yearn_vaults=query_yearn_vaults,
            query_morpho_vaults=query_morpho_vaults,
            query_pendle_yield_tokens=query_pendle_yield_tokens,
            query_morpho_reward_distributors=query_morpho_reward_distributors,
            query_aura_pools=query_aura_pools,
        )
        self.exchange_tasks = ExchangeTasks(greenlet_manager, database, exchange_manager)
        self.reminder_tasks = ReminderTasks(greenlet_manager, database, msg_aggregator)
        self.prepared_cryptocompare_query = False
        self.running_greenlets: dict[Callable, list[gevent.Greenlet]] = {}
        self.deactivate_premium = deactivate_premium
        self.activate_premium = activate_premium
        self.query_balances = query_balances
        self.last_balance_query_ts = Timestamp(0)
        self.last_premium_status_check = ts_now()
        self.msg_aggregator = msg_aggregator
        self.premium_check_retries = 0
        self.premium_sync_manager: Optional[PremiumSyncManager] = premium_sync_manager
        self.data_updater = data_updater
        self.username = username

        self.potential_tasks: list[Callable[[], Optional[list[gevent.Greenlet]]]] = [
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
        self.schedule_lock = gevent.lock.Semaphore()

    def _maybe_schedule_db_upload(self) -> Optional[list[gevent.Greenlet]]:
        assert self.premium_sync_manager is not None, 'caller should make sure premium sync manager exists'  # noqa: E501
        if self.premium_sync_manager.check_if_should_sync(force_upload=False) is False:
            return None

        log.debug('Scheduling task for DB upload to server')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Upload data to server',
            exception_is_error=True,
            method=self.premium_sync_manager.maybe_upload_data_to_server,
        )]

    def _prepare_cryptocompare_queries(self) -> None:
        """
        Prepare the queries to do to cryptocompare
        Runs only once and then has a number of queries prepared for the task manager to schedule
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

    def _maybe_schedule_cryptocompare_query(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules a cryptocompare query for a single asset history"""
        if self.prepared_cryptocompare_query is False:
            self._prepare_cryptocompare_queries()

        if len(self.cryptocompare_queries) == 0:
            return None

        # If there is already a cryptocompary query running don't schedule another
        if any(
                'Cryptocompare historical prices' in x.task_name
                for x in self.greenlet_manager.greenlets
        ):
            return None

        now_ts = ts_now()
        # Make sure there is a long enough period  between an asset's histohour query
        # to avoid getting rate limited by cryptocompare
        if now_ts - self.cryptocompare.last_histohour_query_ts <= CRYPTOCOMPARE_HISTOHOUR_FREQUENCY:  # noqa: E501
            return None

        query = self.cryptocompare_queries.pop()
        task_name = f'Cryptocompare historical prices {query.from_asset} / {query.to_asset} query'
        log.debug(f'Scheduling task for {task_name}')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=False,
            method=self.cryptocompare.query_and_store_historical_data,
            from_asset=query.from_asset,
            to_asset=query.to_asset,
            timestamp=now_ts,
        )]

    def _maybe_schedule_xpub_derivation(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_schedule_xpub_derivation()

    def _maybe_query_evm_transactions(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the evm transaction query task if enough time has passed"""
        return self.blockchain_tasks.maybe_query_evm_transactions()

    def _maybe_schedule_evm_txreceipts(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the evm transaction receipts query task"""
        return self.blockchain_tasks.maybe_schedule_evm_txreceipts()


    def _maybe_schedule_exchange_history_query(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the exchange history query task if enough time has passed"""
        return self.exchange_tasks.maybe_schedule_exchange_history_query()

    def _maybe_decode_evm_transactions(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the evm transaction decoding task"""
        return self.blockchain_tasks.maybe_decode_evm_transactions()
    def _maybe_check_premium_status(self) -> None:
        """
        Validates the premium status of the account and if the credentials are not valid
        it retries 3 times before deactivating the user's premium status. If the
        credentials are valid and the premium status is not correct it will reactivate
        the user's premium status.
        """
        now = ts_now()
        if now - self.last_premium_status_check < PREMIUM_STATUS_CHECK:
            return

        log.debug('Running the premium status check')
        with self.database.conn.read_ctx() as cursor:
            db_credentials = self.database.get_rotkehlchen_premium(cursor)
        if db_credentials is None:
            self.last_premium_status_check = now
            return

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
                return
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
            log.debug('Premium check failed due to authentication error. Sending deactivate message')  # noqa: E501
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

    def _maybe_update_snapshot_balances(self) -> Optional[list[gevent.Greenlet]]:
        """
        Update the balances of a user if the difference between last time they were updated
        and the current time exceeds the `balance_save_frequency`.
        """
        with self.database.conn.read_ctx() as read_cursor:
            if not self.database.should_save_balances(
                cursor=read_cursor,
                last_query_ts=self.last_balance_query_ts,
            ):
                return None

        maybe_detect_new_tokens(self.database)
        task_name = 'Periodically update snapshot balances'
        log.debug(f'Scheduling task to {task_name}')
        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=True,
            method=self.query_balances,
            requested_save_data=True,
            save_despite_errors=False,
            timestamp=None,
            ignore_cache=True,
        )]

    def _maybe_query_produced_blocks(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the blocks production query if enough time has passed"""
        return self.blockchain_tasks.maybe_query_produced_blocks()

    def _maybe_query_withdrawals(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the eth withdrawal query if enough time has passed"""
        return self.blockchain_tasks.maybe_query_withdrawals()

    def _maybe_detect_withdrawal_exits(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the task that detects if any withdrawals should be exits"""
        return self.blockchain_tasks.maybe_detect_withdrawal_exits()

    def _maybe_run_events_processing(self) -> Optional[list[gevent.Greenlet]]:
        """Schedules the events processing task which may combine/edit events"""
        return self.blockchain_tasks.maybe_run_events_processing()


    def _maybe_update_yearn_vaults(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_update_yearn_vaults()

    def _maybe_update_morpho_cache(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_update_morpho_cache()

        return greenlets if len(greenlets) > 0 else None

    def _maybe_update_pendle_cache(self) -> Optional[list[gevent.Greenlet]]:
    def _maybe_update_aura_pools(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_update_aura_pools()


    def _maybe_check_data_updates(self) -> Optional[list[gevent.Greenlet]]:
        """
        Function that schedules the data update task if either there is no data update
        cache yet or this cache is older than `DATA_UPDATES_REFRESH`
        """
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_DATA_UPDATES_TS, DATA_UPDATES_REFRESH) is False:  # noqa: E501
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Data update task',
            exception_is_error=True,
            method=self.data_updater.check_for_updates,
        )]

    def _maybe_detect_evm_accounts(self) -> Optional[list[gevent.Greenlet]]:
    def _maybe_update_ilk_cache(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_update_ilk_cache()

    def _maybe_detect_new_spam_tokens(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_detect_new_spam_tokens()

    def _maybe_update_owned_assets(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_update_owned_assets()

            task_name='Update owned assets in globaldb',
            exception_is_error=True,
            method=update_owned_assets,
            user_db=self.database,
        )]

    def _maybe_update_aave_v3_underlying_assets(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_update_aave_v3_underlying_assets()

    def _maybe_update_spark_underlying_assets(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_update_spark_underlying_assets()

        """
        if should_run_periodic_task(
            database=self.database,
            refresh_period=WEEK_IN_SECONDS,
            key_name=DBCacheStatic.LAST_SPARK_ASSETS_UPDATE,
        ) is False:
            return None

        return [self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name='Update Spark underlying assets in globaldb',
            exception_is_error=True,
            method=update_spark_underlying_assets,
            chains_aggregator=self.chains_aggregator,
        )]

    def _maybe_query_monerium(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_query_monerium()

    def _maybe_query_gnosispay(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_query_gnosispay()

    def _maybe_create_calendar_reminder(self) -> Optional[list[gevent.Greenlet]]:
        return self.reminder_tasks.maybe_create_calendar_reminder()

    def _maybe_trigger_calendar_reminder(self) -> Optional[list[gevent.Greenlet]]:
        return self.reminder_tasks.maybe_trigger_calendar_reminder()

    def _maybe_delete_past_calendar_events(self) -> Optional[list[gevent.Greenlet]]:
        return self.reminder_tasks.maybe_delete_past_calendar_events()

    def _maybe_query_graph_delegated_tokens(self) -> Optional[list[gevent.Greenlet]]:
        return self.blockchain_tasks.maybe_query_graph_delegated_tokens()

    def _schedule(self) -> None:
        """Schedules background tasks"""
        self.greenlet_manager.clear_finished()
        # Also clear methods mapping in the task manager
        self.running_greenlets = {
            method: greenlets
            for method, greenlets in self.running_greenlets.items()
            if not all(greenlet.dead for greenlet in greenlets)
        }
        current_greenlets = len(self.greenlet_manager.greenlets) + len(self.api_task_greenlets)
        not_proceed = current_greenlets >= self.max_tasks_num
        log.debug(
            f'At task scheduling. Current greenlets: {current_greenlets} '
            f'Max greenlets: {self.max_tasks_num}. '
            f'{"Will not schedule" if not_proceed else "Will schedule"}.',
        )
        if not_proceed:
            return  # too busy

        random.shuffle(self.potential_tasks)
        max_tasks = min(self.max_tasks_num - current_greenlets, len(self.potential_tasks))

        spawned_new = 0
        for scheduling_fn in self.potential_tasks:
            if spawned_new >= max_tasks:
                break  # no more task slots left
            if scheduling_fn in self.running_greenlets:
                continue  # the specified task is already running
            new_greenlets = scheduling_fn()
            if new_greenlets is None:
                continue  # The scheduling function for the specific task decided to not schedule it  # noqa: E501
            self.running_greenlets[scheduling_fn] = new_greenlets
            spawned_new += 1

    def schedule(self) -> None:
        """Schedules background task while holding the scheduling lock

        Only if should_schedule has been set to True, which happens after the first
        time the user loads up the dashboard. This is to avoid any background tasks running
        during user migrations, db upgrades and asset upgrades.

        Used during logout to make sure no task is being scheduled at the same time
        as logging out
        """
        if self.should_schedule is False:
            return

        with self.schedule_lock:
            if self.should_schedule:  # adding this check here to protect against going to schedule during logout/shutdown once task manager has been cleared and DB has been deleted  # noqa: E501
                self._schedule()

    def clear(self) -> None:
        """Ensure that no task is kept referenced. Used when removing the task manager"""
        for task_list in self.running_greenlets.values():
            gevent.killall(task_list)

        self.running_greenlets.clear()
        self.should_schedule = False
