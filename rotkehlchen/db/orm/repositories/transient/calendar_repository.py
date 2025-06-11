"""Repository for calendar events and reminders management"""


from sqlalchemy import and_, delete, func, select

from rotkehlchen.db.orm.user_db_models import Calendar as CalendarEvent, CalendarReminder
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import Timestamp


class CalendarRepository(BaseRepository[CalendarEvent]):
    """Repository for managing calendar events and reminders"""

    def __init__(self, session):
        super().__init__(session, CalendarEvent)

    def add_event(
        self,
        name: str,
        description: str,
        timestamp: Timestamp,
        color: str | None = None,
        auto_delete: bool = False,
    ) -> CalendarEvent:
        """Add a calendar event"""
        event = CalendarEvent(
            name=name,
            description=description,
            timestamp=int(timestamp),
            color=color,
            auto_delete=auto_delete,
        )
        return self.add(event)

    def get_event(self, identifier: int) -> CalendarEvent | None:
        """Get an event by identifier"""
        return self.get(identifier=identifier)

    def get_events(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
        name: str | None = None,
        auto_delete: bool | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[CalendarEvent]:
        """Get calendar events with filters"""
        query = select(CalendarEvent)

        if from_timestamp is not None:
            query = query.filter(CalendarEvent.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(CalendarEvent.timestamp <= int(to_timestamp))

        if name:
            query = query.filter(CalendarEvent.name.like(f'%{name}%'))

        if auto_delete is not None:
            query = query.filter_by(auto_delete=auto_delete)

        # Order by timestamp
        query = query.order_by(CalendarEvent.timestamp)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def update_event(
        self,
        identifier: int,
        name: str | None = None,
        description: str | None = None,
        timestamp: Timestamp | None = None,
        color: str | None = None,
        auto_delete: bool | None = None,
    ) -> CalendarEvent | None:
        """Update a calendar event"""
        event = self.get_event(identifier)
        if not event:
            return None

        if name is not None:
            event.name = name
        if description is not None:
            event.description = description
        if timestamp is not None:
            event.timestamp = int(timestamp)
        if color is not None:
            event.color = color
        if auto_delete is not None:
            event.auto_delete = auto_delete

        return self.update(event)

    def delete_event(self, identifier: int) -> bool:
        """Delete a calendar event and its reminders"""
        # Delete associated reminders first
        self.delete_reminders_for_event(identifier)

        # Delete the event
        return self.delete_by(identifier=identifier) > 0

    def get_upcoming_events(
        self,
        after_timestamp: Timestamp,
        limit: int | None = None,
    ) -> list[CalendarEvent]:
        """Get upcoming events after timestamp"""
        query = select(CalendarEvent).filter(
            CalendarEvent.timestamp > int(after_timestamp),
        ).order_by(CalendarEvent.timestamp)

        if limit is not None:
            query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def get_past_events_to_delete(self, before_timestamp: Timestamp) -> list[CalendarEvent]:
        """Get past events marked for auto-deletion"""
        stmt = select(CalendarEvent).filter(
            and_(
                CalendarEvent.timestamp < int(before_timestamp),
                CalendarEvent.auto_delete,
            ),
        )

        return list(self.session.execute(stmt).scalars().all())

    def delete_old_events(self, before_timestamp: Timestamp) -> int:
        """Delete events marked for auto-deletion before timestamp"""
        events = self.get_past_events_to_delete(before_timestamp)
        count = 0

        for event in events:
            if self.delete_event(event.identifier):
                count += 1

        return count

    # Reminder operations

    def add_reminder(
        self,
        event_id: int,
        secs_before: int,
    ) -> CalendarReminder:
        """Add a reminder for an event"""
        reminder = CalendarReminder(
            event_id=event_id,
            secs_before=secs_before,
        )
        self.session.add(reminder)
        self.session.flush()
        return reminder

    def get_reminders_for_event(self, event_id: int) -> list[CalendarReminder]:
        """Get all reminders for an event"""
        stmt = select(CalendarReminder).filter_by(
            event_id=event_id,
        ).order_by(CalendarReminder.secs_before.desc())

        return list(self.session.execute(stmt).scalars().all())

    def delete_reminder(self, identifier: int) -> bool:
        """Delete a specific reminder"""
        stmt = delete(CalendarReminder).filter_by(identifier=identifier)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount > 0

    def delete_reminders_for_event(self, event_id: int) -> int:
        """Delete all reminders for an event"""
        stmt = delete(CalendarReminder).filter_by(event_id=event_id)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def get_due_reminders(self, current_timestamp: Timestamp) -> list[tuple[CalendarEvent, CalendarReminder]]:
        """Get events with reminders that are due"""
        # Join events with reminders
        query = (
            select(CalendarEvent, CalendarReminder)
            .join(CalendarReminder, CalendarEvent.identifier == CalendarReminder.event_id)
            .filter(
                CalendarEvent.timestamp - CalendarReminder.secs_before <= int(current_timestamp),
            )
            .order_by(CalendarEvent.timestamp)
        )

        results = self.session.execute(query).all()
        return [(row.CalendarEvent, row.CalendarReminder) for row in results]

    def event_exists(self, name: str, timestamp: Timestamp) -> bool:
        """Check if event with name and timestamp exists"""
        stmt = select(CalendarEvent).filter_by(
            name=name,
            timestamp=int(timestamp),
        ).limit(1)
        return self.session.execute(stmt).scalar() is not None

    def get_events_count(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
    ) -> int:
        """Get count of events"""
        query = select(func.count()).select_from(CalendarEvent)

        if from_timestamp is not None:
            query = query.filter(CalendarEvent.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(CalendarEvent.timestamp <= int(to_timestamp))

        return self.session.execute(query).scalar() or 0

    def bulk_add_events(
        self,
        events_data: list[dict[str, any]],
    ) -> list[CalendarEvent]:
        """Bulk add multiple events"""
        events = []

        for data in events_data:
            event = CalendarEvent(
                name=data['name'],
                description=data['description'],
                timestamp=int(data['timestamp']),
                color=data.get('color'),
                auto_delete=data.get('auto_delete', False),
            )
            self.session.add(event)
            events.append(event)

        self.session.flush()
        return events
