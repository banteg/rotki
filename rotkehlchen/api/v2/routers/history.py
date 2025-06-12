"""History router for transaction history and events endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from rotkehlchen.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.api.v2.services.history import HistoryService
from rotkehlchen.history.events.structures.base import HistoryEventType

router = APIRouter()


class HistoryResponse(BaseModel):
    """Response model for history operations"""
    result: Any
    message: str = ''


class HistoryEventRequest(BaseModel):
    """Request model for creating history events"""
    event_identifier: str
    sequence_index: int
    timestamp: int = Field(ge=0)
    location: str
    event_type: HistoryEventType
    event_subtype: str | None = None
    asset: str
    balance: dict[str, str]
    location_label: str | None = None
    notes: str | None = None
    counterparty: str | None = None
    extra_data: dict[str, Any] | None = None


class HistoryEventFilterRequest(BaseModel):
    """Request model for filtering history events"""
    from_timestamp: int = Field(0, ge=0)
    to_timestamp: int = Field(2147483647, ge=0)
    event_types: list[HistoryEventType] | None = None
    event_subtypes: list[str] | None = None
    locations: list[str] | None = None
    assets: list[str] | None = None
    counterparties: list[str] | None = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


def get_history_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> HistoryService:
    """Get history service instance"""
    return HistoryService(db_service)


@router.get('/events')
async def get_history_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
    event_types: list[HistoryEventType] | None = Query(None),
    locations: list[str] | None = Query(None),
    assets: list[str] | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> HistoryResponse:
    """Get history events with filtering"""
    events = history_service.get_history_events(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        event_types=event_types,
        locations=locations,
        assets=assets,
        limit=limit,
        offset=offset,
    )

    return HistoryResponse(
        result={
            'events': events,
            'total': len(events),
        },
    )


@router.post('/events')
async def create_history_event(
    event_data: HistoryEventRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
) -> HistoryResponse:
    """Create a new history event"""
    event = history_service.create_history_event(
        event_identifier=event_data.event_identifier,
        sequence_index=event_data.sequence_index,
        timestamp=event_data.timestamp,
        location=event_data.location,
        event_type=event_data.event_type,
        event_subtype=event_data.event_subtype,
        asset=event_data.asset,
        balance=event_data.balance,
        location_label=event_data.location_label,
        notes=event_data.notes,
        counterparty=event_data.counterparty,
        extra_data=event_data.extra_data,
    )

    return HistoryResponse(
        result={'event_id': event.identifier},
        message='History event created successfully',
    )


@router.put('/events/{event_id}')
async def update_history_event(
    event_id: int,
    event_data: HistoryEventRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
) -> HistoryResponse:
    """Update an existing history event"""
    success = history_service.update_history_event(
        event_id=event_id,
        **event_data.model_dump(),
    )

    if not success:
        return HistoryResponse(
            result={'success': False},
            message='Event not found',
        )

    return HistoryResponse(
        result={'success': True},
        message='History event updated successfully',
    )


@router.delete('/events/{event_id}')
async def delete_history_event(
    event_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
) -> HistoryResponse:
    """Delete a history event"""
    success = history_service.delete_history_event(event_id)

    if not success:
        return HistoryResponse(
            result={'success': False},
            message='Event not found',
        )

    return HistoryResponse(
        result={'success': True},
        message='History event deleted successfully',
    )


@router.post('/process')
async def process_history(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> HistoryResponse:
    """Process history for accounting"""
    task_id = history_service.process_history(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )

    return HistoryResponse(
        result={'task_id': task_id},
        message='History processing started',
    )


@router.get('/status')
async def get_history_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
) -> HistoryResponse:
    """Get history processing status"""
    status = history_service.get_processing_status()

    return HistoryResponse(result=status)


@router.post('/export')
async def export_history(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[HistoryService, Depends(get_history_service)],
    directory_path: str,
) -> HistoryResponse:
    """Export history data to CSV"""
    file_path = history_service.export_history(directory_path)

    return HistoryResponse(
        result={'file_path': file_path},
        message='History exported successfully',
    )
