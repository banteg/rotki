"""Calendar router for calendar and reminder endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.calendar import CalendarService
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