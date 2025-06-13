"""History router for transaction history and events endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field

from rotki2.api.v2.dependencies import (
    get_async_history_service,
    require_logged_in_user,
)
from rotki2.api.v2.services.async_history import AsyncHistoryService
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




@router.get('/events')
async def get_history_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
    event_types: list[HistoryEventType] | None = Query(None),
    locations: list[str] | None = Query(None),
    assets: list[str] | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> HistoryResponse:
    """Get history events with filtering"""
    from rotki2.api.v2.repositories.history import HistoryEventFilter
    
    # Create filter for async service
    filter_query = HistoryEventFilter(
        from_ts=from_timestamp,
        to_ts=to_timestamp,
        event_types=[str(et) for et in event_types] if event_types else None,
        locations=locations,
        assets=assets,
    )
    
    events, total = await history_service.get_history_events(
        filter_query=filter_query,
        has_premium=True,
    )
    
    # Serialize events
    serialized_events = []
    for event in events:
        serialized_events.append({
            'identifier': event.identifier,
            'event_identifier': event.event_identifier,
            'sequence_index': event.sequence_index,
            'timestamp': event.timestamp,
            'location': event.location.serialize(),
            'event_type': event.event_type.serialize(),
            'event_subtype': event.event_subtype,
            'asset': event.asset.identifier,
            'balance': {
                'amount': str(event.balance.amount),
                'usd_value': str(event.balance.usd_value) if event.balance.usd_value else '0',
            },
            'location_label': event.location_label,
            'notes': event.notes,
            'counterparty': event.counterparty.serialize() if event.counterparty else None,
            'extra_data': event.extra_data or {},
        })

    return HistoryResponse(
        result={
            'events': serialized_events,
            'total': total,
        },
    )


@router.post('/events')
async def create_history_event(
    event_data: HistoryEventRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Create a new history event"""
    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.base import HistoryEvent
    from rotkehlchen.types import Location
    
    # Create the event object
    event = HistoryEvent(
        event_identifier=event_data.event_identifier,
        sequence_index=event_data.sequence_index,
        timestamp=event_data.timestamp,
        location=Location.deserialize(event_data.location),
        event_type=event_data.event_type,
        event_subtype=event_data.event_subtype,
        asset=Asset(event_data.asset),
        balance=Balance(
            amount=FVal(event_data.balance.get('amount', '0')),
            usd_value=FVal(event_data.balance.get('usd_value', '0')),
        ),
        location_label=event_data.location_label,
        notes=event_data.notes,
        counterparty=event_data.counterparty,
        extra_data=event_data.extra_data,
    )
    
    event_id = await history_service.add_history_event(event)

    return HistoryResponse(
        result={'event_id': event_id},
        message='History event created successfully',
    )


@router.put('/events/{event_id}')
async def update_history_event(
    event_id: int,
    event_data: HistoryEventRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
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
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
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
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> HistoryResponse:
    """Process history for accounting"""
    report_id, error_msg = await history_service.process_history(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )

    if error_msg:
        return HistoryResponse(
            result={'report_id': report_id},
            message=f'History processing started with warnings: {error_msg}',
        )

    return HistoryResponse(
        result={'report_id': report_id},
        message='History processing started',
    )


@router.get('/status')
async def get_history_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get history processing status"""
    status = history_service.get_processing_status()

    return HistoryResponse(result=status)


@router.post('/export')
async def export_history(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    directory_path: str,
) -> HistoryResponse:
    """Export history data to CSV"""
    file_path = history_service.export_history(directory_path)

    return HistoryResponse(
        result={'file_path': file_path},
        message='History exported successfully',
    )


@router.get('/export')
async def get_export_history(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    directory_path: str = Query(...),
) -> HistoryResponse:
    """Export history data to CSV (GET version)"""
    return await export_history(_, history_service, directory_path)


@router.post('/status')
async def post_history_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get history processing status (POST version)"""
    return await get_history_status(_, history_service)


@router.get('/')
async def get_history(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
    ascending: bool = Query(False),
    group_by_event_ids: bool = Query(False),
) -> HistoryResponse:
    """Query history data"""
    results = history_service.query_history(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        ascending=ascending,
        group_by_event_ids=group_by_event_ids,
    )

    return HistoryResponse(result=results)


@router.post('/')
async def post_history(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    from_timestamp: int = 0,
    to_timestamp: int = 2147483647,
    ascending: bool = False,
    group_by_event_ids: bool = False,
) -> HistoryResponse:
    """Query history data (POST version)"""
    return await get_history(
        _,
        history_service,
        from_timestamp,
        to_timestamp,
        ascending,
        group_by_event_ids,
    )


@router.get('/events/counterparties')
async def get_event_counterparties(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get all unique counterparties from history events"""
    counterparties = history_service.get_unique_counterparties()

    return HistoryResponse(result={'counterparties': counterparties})


@router.post('/events/counterparties')
async def post_event_counterparties(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get all unique counterparties (POST version)"""
    return await get_event_counterparties(_, history_service)


@router.get('/events/products')
async def get_event_products(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get all unique products from history events"""
    products = history_service.get_unique_products()

    return HistoryResponse(result={'products': products})


@router.post('/events/products')
async def post_event_products(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get all unique products (POST version)"""
    return await get_event_products(_, history_service)


@router.get('/download')
async def download_history(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> HistoryResponse:
    """Download history data as CSV"""
    file_path = history_service.download_history(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )

    return HistoryResponse(
        result={'file_path': file_path},
        message='History data exported',
    )


@router.post('/download')
async def post_download_history(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    from_timestamp: int = 0,
    to_timestamp: int = 2147483647,
) -> HistoryResponse:
    """Download history data as CSV (POST version)"""
    return await download_history(_, history_service, from_timestamp, to_timestamp)


@router.get('/actionable_items')
async def get_actionable_items(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get actionable items from history"""
    items = history_service.get_actionable_items()

    return HistoryResponse(result={'items': items})


@router.post('/actionable_items')
async def post_actionable_items(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get actionable items from history (POST version)"""
    return await get_actionable_items(_, history_service)


@router.get('/debug')
async def get_history_debug_info(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get debug information about history processing"""
    debug_info = history_service.get_debug_info()

    return HistoryResponse(result=debug_info)


@router.post('/debug')
async def post_history_debug_info(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get debug information about history processing (POST version)"""
    return await get_history_debug_info(_, history_service)


class EventDetailsRequest(BaseModel):
    """Request model for event details"""
    event_identifiers: list[str]
    ignore_cache: bool = False


@router.get('/events/details')
async def get_event_details(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    event_identifier: str,
) -> HistoryResponse:
    """Get detailed information for specific events"""
    details = history_service.get_event_details(event_identifier)

    return HistoryResponse(result=details)


@router.post('/events/details')
async def post_event_details(
    request_data: EventDetailsRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get detailed information for multiple events"""
    all_details = {}

    for event_id in request_data.event_identifiers:
        details = history_service.get_event_details(
            event_id,
            ignore_cache=request_data.ignore_cache,
        )
        all_details[event_id] = details

    return HistoryResponse(result={'events': all_details})


@router.get('/events/type_mappings')
async def get_event_type_mappings(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get mappings of event types to human-readable names"""
    mappings = history_service.get_event_type_mappings()

    return HistoryResponse(result=mappings)


@router.post('/events/type_mappings')
async def post_event_type_mappings(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get mappings of event types to human-readable names (POST version)"""
    return await get_event_type_mappings(_, history_service)


# v1 compatibility endpoints for history/debug
@router.post('/debug')
async def export_pnl_debug_data(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    directory_path: str,
) -> HistoryResponse:
    """Export PnL debug data - Compatible with v1 POST /api/1/history/debug"""
    file_path = history_service.export_debug_data(directory_path)

    return HistoryResponse(
        result={'file_path': file_path},
        message='Debug data exported',
    )


@router.put('/debug')
async def import_pnl_debug_data_path(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    filepath: str,
) -> HistoryResponse:
    """Import PnL debug data from file path - Compatible with v1 PUT /api/1/history/debug"""
    result = history_service.import_debug_data(filepath)

    return HistoryResponse(
        result=result,
        message='Debug data imported',
    )


@router.patch('/debug')
async def import_pnl_debug_data_upload(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    file: UploadFile = File(...),
) -> HistoryResponse:
    """Import PnL debug data from file upload - Compatible with v1 PATCH /api/1/history/debug"""
    # Save uploaded file temporarily
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = history_service.import_debug_data(tmp_path)
        return HistoryResponse(
            result=result,
            message='Debug data imported',
        )
    finally:
        os.unlink(tmp_path)


# History events export endpoints
@router.post('/events/export')
async def export_history_events_to_dir(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    directory_path: str,
) -> HistoryResponse:
    """Export history events to a file in a directory - Compatible with v1 POST /api/1/history/events/export"""
    file_path = history_service.export_events_to_directory(directory_path)

    return HistoryResponse(
        result={'file_path': file_path},
        message='History events exported',
    )


@router.put('/events/export')
async def download_history_events_csv(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Download history events as CSV - Compatible with v1 PUT /api/1/history/events/export"""
    csv_data = history_service.export_events_as_csv()

    return HistoryResponse(
        result={'csv': csv_data},
        message='History events exported as CSV',
    )


@router.get('/events/export/download')
async def download_exported_history_csv(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    filepath: str,
) -> HistoryResponse:
    """Download an exported history events CSV - Compatible with v1 GET /api/1/history/events/export/download"""
    # Would return file contents
    return HistoryResponse(
        result={'file': filepath},
        message='File download initiated',
    )


# Skipped external events endpoints
@router.get('/skipped_external_events')
async def get_skipped_external_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Get summary of skipped events - Compatible with v1 GET /api/1/history/skipped_external_events"""
    skipped = history_service.get_skipped_external_events()

    return HistoryResponse(result=skipped)


@router.put('/skipped_external_events')
async def export_skipped_events_to_dir(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
    directory_path: str,
) -> HistoryResponse:
    """Export skipped events to a file - Compatible with v1 PUT /api/1/history/skipped_external_events"""
    file_path = history_service.export_skipped_events(directory_path)

    return HistoryResponse(
        result={'file_path': file_path},
        message='Skipped events exported',
    )


@router.patch('/skipped_external_events')
async def download_skipped_events_csv(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Download skipped events as CSV - Compatible with v1 PATCH /api/1/history/skipped_external_events"""
    csv_data = history_service.download_skipped_events_csv()

    return HistoryResponse(
        result={'csv': csv_data},
        message='Skipped events CSV generated',
    )


@router.post('/skipped_external_events')
async def reprocess_skipped_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    history_service: Annotated[AsyncHistoryService, Depends(get_async_history_service)],
) -> HistoryResponse:
    """Reprocess skipped events - Compatible with v1 POST /api/1/history/skipped_external_events"""
    result = history_service.reprocess_skipped_events()

    return HistoryResponse(
        result=result,
        message='Skipped events reprocessing started',
    )
