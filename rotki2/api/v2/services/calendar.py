"""Calendar service for managing events and reminders"""
import uuid
from datetime import datetime
from typing import Any

from rotkehlchen.types import Timestamp


class CalendarService:
    """Service for managing calendar events and reminders"""

    def __init__(self) -> None:
        # In-memory storage for now
        self._events: list[dict[str, Any]] = []
        self._reminders: list[dict[str, Any]] = []

    def get_events(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
    ) -> list[dict[str, Any]]:
        """Get calendar events within a time range"""
        filtered_events = []

        for event in self._events:
            event_timestamp = event['timestamp']

            if from_timestamp and event_timestamp < from_timestamp:
                continue
            if to_timestamp and event_timestamp > to_timestamp:
                continue

            filtered_events.append(event)

        # Sort by timestamp
        filtered_events.sort(key=lambda x: x['timestamp'])

        return filtered_events

    def create_event(
        self,
        title: str,
        description: str | None = None,
        timestamp: Timestamp = None,
        event_type: str = 'general',
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new calendar event"""
        valid_event_types = ['general', 'tax_deadline', 'exchange_closure', 'fork', 'airdrop']

        if event_type not in valid_event_types:
            raise ValueError(f'Invalid event type. Must be one of: {", ".join(valid_event_types)}')

        event_id = str(uuid.uuid4())

        event = {
            'id': event_id,
            'title': title,
            'description': description,
            'timestamp': timestamp or Timestamp(int(datetime.now().timestamp())),
            'event_type': event_type,
            'metadata': metadata or {},
            'created_at': Timestamp(int(datetime.now().timestamp())),
        }

        self._events.append(event)

        return event_id

    def get_reminders(self) -> list[dict[str, Any]]:
        """Get all active reminders"""
        # Filter out past non-recurring reminders
        current_time = Timestamp(int(datetime.now().timestamp()))
        active_reminders = []

        for reminder in self._reminders:
            if reminder['recurring'] or reminder['timestamp'] > current_time:
                active_reminders.append(reminder)

        return active_reminders

    def create_reminder(
        self,
        title: str,
        description: str | None = None,
        timestamp: Timestamp = None,
        reminder_type: str = 'general',
        recurring: bool = False,
        interval_days: int | None = None,
    ) -> str:
        """Create a new reminder"""
        valid_reminder_types = ['general', 'tax_payment', 'report_filing', 'portfolio_review']

        if reminder_type not in valid_reminder_types:
            raise ValueError(f'Invalid reminder type. Must be one of: {", ".join(valid_reminder_types)}')

        if recurring and not interval_days:
            raise ValueError('Recurring reminders must specify interval_days')

        reminder_id = str(uuid.uuid4())

        reminder = {
            'id': reminder_id,
            'title': title,
            'description': description,
            'timestamp': timestamp or Timestamp(int(datetime.now().timestamp())),
            'reminder_type': reminder_type,
            'recurring': recurring,
            'interval_days': interval_days,
            'created_at': Timestamp(int(datetime.now().timestamp())),
        }

        self._reminders.append(reminder)

        return reminder_id

    def delete_event(self, event_id: str) -> None:
        """Delete a calendar event"""
        for i, event in enumerate(self._events):
            if event['id'] == event_id:
                del self._events[i]
                return
        raise ValueError(f'Event {event_id} not found')

    def update_event(
        self,
        event_id: str,
        title: str,
        description: str | None = None,
        timestamp: Timestamp | None = None,
        event_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update a calendar event"""
        for event in self._events:
            if event['id'] == event_id:
                event['title'] = title
                if description is not None:
                    event['description'] = description
                if timestamp is not None:
                    event['timestamp'] = timestamp
                if event_type is not None:
                    event['event_type'] = event_type
                if metadata is not None:
                    event['metadata'] = metadata
                event['updated_at'] = Timestamp(int(datetime.now().timestamp()))
                return event
        raise ValueError(f'Event {event_id} not found')

    def get_reminders_for_event(self, event_id: str) -> list[dict[str, Any]]:
        """Get reminders for a specific event"""
        # In a real implementation, reminders would be linked to events
        # For now, return all reminders
        return self.get_reminders()

    def delete_reminder(self, reminder_id: str) -> None:
        """Delete a reminder"""
        for i, reminder in enumerate(self._reminders):
            if reminder['id'] == reminder_id:
                del self._reminders[i]
                return
        raise ValueError(f'Reminder {reminder_id} not found')

    def update_reminder(
        self,
        reminder_id: str,
        title: str,
        description: str | None = None,
        timestamp: Timestamp | None = None,
        reminder_type: str | None = None,
        recurring: bool | None = None,
        interval_days: int | None = None,
    ) -> dict[str, Any]:
        """Update a reminder"""
        for reminder in self._reminders:
            if reminder['id'] == reminder_id:
                reminder['title'] = title
                if description is not None:
                    reminder['description'] = description
                if timestamp is not None:
                    reminder['timestamp'] = timestamp
                if reminder_type is not None:
                    reminder['reminder_type'] = reminder_type
                if recurring is not None:
                    reminder['recurring'] = recurring
                if interval_days is not None:
                    reminder['interval_days'] = interval_days
                reminder['updated_at'] = Timestamp(int(datetime.now().timestamp()))
                return reminder
        raise ValueError(f'Reminder {reminder_id} not found')
