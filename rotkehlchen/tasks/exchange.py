"""Exchange-related scheduled tasks"""

from collections import defaultdict
from typing import Optional
import logging
import random

from rotkehlchen.utils.misc import ts_now

import gevent

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ExchangeLocationID, Location

if False:  # TYPE_CHECKING
    from rotkehlchen.exchanges.manager import ExchangeManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.greenlets.manager import GreenletManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
EXCHANGE_QUERY_FREQUENCY = 3600


class ExchangeTasks:
    """Group exchange related background tasks"""

    def __init__(self, greenlet_manager: 'GreenletManager', database: 'DBHandler', exchange_manager: 'ExchangeManager') -> None:
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.exchange_manager = exchange_manager
        self.last_exchange_query_ts: defaultdict[ExchangeLocationID, int] = defaultdict(int)

    def maybe_schedule_exchange_history_query(self) -> Optional[list[gevent.Greenlet]]:
        if len(self.exchange_manager.connected_exchanges) == 0:
            return None
        now = ts_now()
        queriable_exchanges = []
        with self.database.conn.read_ctx() as cursor:
            for exchange in self.exchange_manager.iterate_exchanges():
                if exchange.location in (Location.BINANCE, Location.BINANCEUS):
                    continue
                queried_range = self.database.get_used_query_range(cursor, f'{exchange.location!s}_trades')
                end_ts = queried_range[1] if queried_range else 0
                if now - max(self.last_exchange_query_ts[exchange.location_id()], end_ts) > EXCHANGE_QUERY_FREQUENCY:
                    queriable_exchanges.append(exchange)
        if len(queriable_exchanges) == 0:
            return None
        exchange = random.choice(queriable_exchanges)
        task_name = f'Query history of {exchange.name} exchange'
        log.debug(f'Scheduling task to {task_name}')
        self.last_exchange_query_ts[exchange.location_id()] = now
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=exchange.query_online_history_events,
                start_ts=0,
                end_ts=now,
            )
        ]
