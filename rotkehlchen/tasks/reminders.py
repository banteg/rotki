"""Calendar reminder related tasks"""

import logging
from collections import defaultdict
from typing import Optional

import gevent

from rotkehlchen.db.calendar import CalendarEntry
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.calendar import (
    CalendarNotification,
    delete_past_calendar_entries,
    maybe_create_calendar_reminders,
    notify_reminders,
)
from rotkehlchen.tasks.utils import should_run_periodic_task
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.types import Timestamp

if False:  # TYPE_CHECKING
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.greenlets.manager import GreenletManager
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ReminderTasks:
    """Group tasks for calendar reminders"""

    def __init__(self, greenlet_manager: 'GreenletManager', database: 'DBHandler', msg_aggregator: 'MessagesAggregator') -> None:
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.last_calendar_reminder_check = Timestamp(0)

    def maybe_create_calendar_reminder(self) -> Optional[list[gevent.Greenlet]]:
        if (
            CachedSettings().get_entry('auto_create_calendar_reminders') is False or
            should_run_periodic_task(
                database=self.database,
                key_name=DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
                refresh_period=DAY_IN_SECONDS,
            ) is False
        ):
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Maybe create calendar reminders',
                exception_is_error=True,
                method=maybe_create_calendar_reminders,
                database=self.database,
            )
        ]

    def maybe_trigger_calendar_reminder(self) -> Optional[list[gevent.Greenlet]]:
        if (now := ts_now()) - self.last_calendar_reminder_check < 60 * 5:
            return None
        reminders: dict[int, list[CalendarNotification]] = defaultdict(list)
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT event.identifier, event.name, event.description, event.counterparty, '
                'event.timestamp, event.address, event.blockchain, event.color, '
                'event.auto_delete, reminder.identifier, reminder.secs_before FROM '
                'calendar_reminders AS reminder LEFT JOIN calendar AS event '
                'ON reminder.event_id = event.identifier WHERE '
                '? > event.timestamp - reminder.secs_before '
                'ORDER BY event.identifier, reminder.secs_before ASC',
                (now,),
            )
            for row in cursor:
                reminders[row[0]].append(
                    CalendarNotification(
                        event=CalendarEntry.deserialize_from_db(row[:9]),
                        identifier=row[9],
                        secs_before=row[10],
                    )
                )
        if len(reminders) == 0:
            return None
        self.last_calendar_reminder_check = now
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Notify calendar reminders',
                exception_is_error=True,
                method=notify_reminders,
                reminders=reminders,
                database=self.database,
                msg_aggregator=self.msg_aggregator,
            )
        ]

    def maybe_delete_past_calendar_events(self) -> Optional[list[gevent.Greenlet]]:
        if should_run_periodic_task(self.database, DBCacheStatic.LAST_DELETE_PAST_CALENDAR_EVENTS, DAY_IN_SECONDS) is False:
            return None
        return [
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name='Delete old calendar entries',
                exception_is_error=True,
                method=delete_past_calendar_entries,
                database=self.database,
            )
        ]
