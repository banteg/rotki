"""Repository for calendar events and reminders."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.calendar import CalendarEvent, CalendarReminder

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CalendarRepository(AsyncBaseRepository[CalendarEvent]):
    """Repository for handling calendar events."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, CalendarEvent)

    async def get_events_in_range(
        self,
        start_timestamp: int,
        end_timestamp: int,
    ) -> list[CalendarEvent]:
        """Get calendar events within a timestamp range.
        
        Args:
            start_timestamp: Start timestamp
            end_timestamp: End timestamp
            
        Returns:
            List of calendar events
        """
        result = await self.session.exec(
            select(CalendarEvent).where(
                col(CalendarEvent.timestamp) >= start_timestamp,
                col(CalendarEvent.timestamp) <= end_timestamp,
            ).order_by(CalendarEvent.timestamp)
        )
        return list(result.all())

    async def get_upcoming_events(self, limit: int = 10) -> list[CalendarEvent]:
        """Get upcoming calendar events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of upcoming calendar events
        """
        current_timestamp = int(datetime.now().timestamp())
        result = await self.session.exec(
            select(CalendarEvent)
            .where(col(CalendarEvent.timestamp) > current_timestamp)
            .order_by(CalendarEvent.timestamp)
            .limit(limit)
        )
        return list(result.all())

    async def get_events_by_type(self, event_type: str) -> list[CalendarEvent]:
        """Get calendar events by type.
        
        Args:
            event_type: The event type to filter by
            
        Returns:
            List of calendar events
        """
        result = await self.session.exec(
            select(CalendarEvent).where(
                col(CalendarEvent.event_type) == event_type
            ).order_by(CalendarEvent.timestamp)
        )
        return list(result.all())


class CalendarReminderRepository(AsyncBaseRepository[CalendarReminder]):
    """Repository for handling calendar reminders."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, CalendarReminder)

    async def get_reminders_for_event(self, event_id: int) -> list[CalendarReminder]:
        """Get all reminders for a specific event.
        
        Args:
            event_id: The calendar event ID
            
        Returns:
            List of reminders for the event
        """
        result = await self.session.exec(
            select(CalendarReminder).where(
                col(CalendarReminder.event_id) == event_id
            )
        )
        return list(result.all())

    async def get_pending_reminders(self) -> list[CalendarReminder]:
        """Get all pending reminders that need to be sent.
        
        Returns:
            List of pending reminders
        """
        current_timestamp = int(datetime.now().timestamp())
        result = await self.session.exec(
            select(CalendarReminder).where(
                col(CalendarReminder.reminded) == False,  # noqa: E712
                col(CalendarReminder.remind_timestamp) <= current_timestamp,
            )
        )
        return list(result.all())

    async def mark_as_reminded(self, reminder_id: int) -> bool:
        """Mark a reminder as sent.
        
        Args:
            reminder_id: The reminder ID
            
        Returns:
            True if updated, False if not found
        """
        reminder = await self.get_by_id(reminder_id)
        if reminder:
            reminder.reminded = True
            self.session.add(reminder)
            await self.session.commit()
            return True
        return False

    async def create_reminder(
        self,
        event_id: int,
        remind_timestamp: int,
    ) -> CalendarReminder:
        """Create a new reminder for an event.
        
        Args:
            event_id: The calendar event ID
            remind_timestamp: When to send the reminder
            
        Returns:
            Created CalendarReminder instance
        """
        reminder = CalendarReminder(
            event_id=event_id,
            remind_timestamp=remind_timestamp,
            reminded=False,
        )
        return await self.create(reminder)