"""Calendar router for calendar and reminder endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.calendar import CalendarService
from rotkehlchen.types import Timestamp

router = APIRouter()


class CalendarResponse(BaseModel):
    """Response model for calendar operations"""
    result: dict[str, Any] | list[dict[str, Any]]
    message: str = ''


class CalendarEventRequest(BaseModel):
    """Request model for calendar events"""
    title: str
    description: str | None = None
    timestamp: Timestamp
    event_type: str
    metadata: dict[str, Any] | None = None


class ReminderRequest(BaseModel):
    """Request model for reminders"""
    title: str
    description: str | None = None
    timestamp: Timestamp
    reminder_type: str
    recurring: bool = False
    interval_days: int | None = None


def get_calendar_service() -> CalendarService:
    """Get calendar service instance"""
    return CalendarService()


@router.get('/')
async def get_calendar_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    from_timestamp: Timestamp | None = None,
    to_timestamp: Timestamp | None = None,
) -> CalendarResponse:
    """Get calendar events within a time range"""
    events = service.get_events(from_timestamp, to_timestamp)

    return CalendarResponse(result=events)


@router.post('/')
async def create_calendar_event(
    event_data: CalendarEventRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Create a new calendar event"""
    try:
        event_id = service.create_event(
            title=event_data.title,
            description=event_data.description,
            timestamp=event_data.timestamp,
            event_type=event_data.event_type,
            metadata=event_data.metadata,
        )

        return CalendarResponse(
            result={'event_id': event_id},
            message='Calendar event created successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get('/reminders')
async def get_reminders(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Get all active reminders"""
    reminders = service.get_reminders()

    return CalendarResponse(result=reminders)


@router.post('/reminders')
async def create_reminder(
    reminder_data: ReminderRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Create a new reminder"""
    try:
        reminder_id = service.create_reminder(
            title=reminder_data.title,
            description=reminder_data.description,
            timestamp=reminder_data.timestamp,
            reminder_type=reminder_data.reminder_type,
            recurring=reminder_data.recurring,
            interval_days=reminder_data.interval_days,
        )

        return CalendarResponse(
            result={'reminder_id': reminder_id},
            message='Reminder created successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post('/')
async def query_calendar_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    from_timestamp: Timestamp | None = None,
    to_timestamp: Timestamp | None = None,
) -> CalendarResponse:
    """Query calendar events - Compatible with v1 POST /api/1/calendar"""
    return await get_calendar_events(_, service, from_timestamp, to_timestamp)


@router.put('/')
async def create_calendar_event_v1(
    event_data: CalendarEventRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Create a calendar event - Compatible with v1 PUT /api/1/calendar"""
    return await create_calendar_event(event_data, _, service)


@router.delete('/')
async def delete_calendar_event(
    event_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Delete a calendar event - Compatible with v1 DELETE /api/1/calendar"""
    try:
        service.delete_event(event_id)
        return CalendarResponse(
            result={'success': True},
            message='Calendar event deleted successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.patch('/')
async def update_calendar_event(
    event_id: str,
    event_data: CalendarEventRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Update a calendar event - Compatible with v1 PATCH /api/1/calendar"""
    try:
        updated_event = service.update_event(
            event_id=event_id,
            title=event_data.title,
            description=event_data.description,
            timestamp=event_data.timestamp,
            event_type=event_data.event_type,
            metadata=event_data.metadata,
        )

        return CalendarResponse(
            result=updated_event,
            message='Calendar event updated successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post('/reminders')
async def query_calendar_reminders(
    event_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Query reminders for an event - Compatible with v1 POST /api/1/calendar/reminders"""
    reminders = service.get_reminders_for_event(event_id)
    return CalendarResponse(result={'reminders': reminders})


@router.put('/reminders')
async def create_reminder_v1(
    reminder_data: ReminderRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Create calendar reminders - Compatible with v1 PUT /api/1/calendar/reminders"""
    return await create_reminder(reminder_data, _, service)


@router.delete('/reminders')
async def delete_reminder(
    reminder_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Delete a reminder - Compatible with v1 DELETE /api/1/calendar/reminders"""
    try:
        service.delete_reminder(reminder_id)
        return CalendarResponse(
            result={'success': True},
            message='Reminder deleted successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.patch('/reminders')
async def update_reminder(
    reminder_id: str,
    reminder_data: ReminderRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> CalendarResponse:
    """Update a reminder - Compatible with v1 PATCH /api/1/calendar/reminders"""
    try:
        updated_reminder = service.update_reminder(
            reminder_id=reminder_id,
            title=reminder_data.title,
            description=reminder_data.description,
            timestamp=reminder_data.timestamp,
            reminder_type=reminder_data.reminder_type,
            recurring=reminder_data.recurring,
            interval_days=reminder_data.interval_days,
        )

        return CalendarResponse(
            result=updated_reminder,
            message='Reminder updated successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
