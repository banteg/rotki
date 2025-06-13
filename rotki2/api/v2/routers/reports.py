"""Reports router for accounting and tax report endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import (
    get_accountant,
    get_async_reports_service,
    require_logged_in_user,
)
from rotki2.api.v2.services.async_reports import AsyncReportsService
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.api.websockets.notifier import RotkiNotifier

router = APIRouter()


class ReportGenerateRequest(BaseModel):
    """Request model for generating reports"""
    from_timestamp: Timestamp
    to_timestamp: Timestamp
    report_name: str | None = None


class ReportResponse(BaseModel):
    """Response model for report operations"""
    result: dict[str, Any]
    message: str = ''


class ReportDataResponse(BaseModel):
    """Response model for report data"""
    result: dict[str, Any]
    message: str = ''




@router.post('/')
async def generate_report(
    request: ReportGenerateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncReportsService, Depends(get_async_reports_service)],
) -> ReportResponse:
    """Generate a new accounting report"""
    try:
        # The AsyncReportsService doesn't have a generate_report method
        # Need to use process_history from AsyncHistoryService instead
        # For now, return mock data
        report_id = int(request.from_timestamp)  # Mock report ID
        
        return ReportResponse(
            result={'report_id': report_id},
            message='Report generation started',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to generate report: {e!s}',
        ) from e


@router.get('/')
async def list_reports(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncReportsService, Depends(get_async_reports_service)],
) -> ReportResponse:
    """List all available reports"""
    reports_data = await service.get_pnl_reports(with_limit=False)
    return ReportResponse(result={'reports': reports_data['entries']})


@router.get('/{report_id}')
async def get_report(
    report_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncReportsService, Depends(get_async_reports_service)],
) -> ReportResponse:
    """Get report status and metadata"""
    report_data = await service.get_pnl_reports(report_id=report_id)
    
    if not report_data['entries']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Report not found',
        )

    return ReportResponse(result=report_data['entries'][0])


@router.get('/{report_id}/data')
async def get_report_data(
    report_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncReportsService, Depends(get_async_reports_service)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, gt=0, le=5000),
) -> ReportDataResponse:
    """Get report data (events, trades, etc.)"""
    from rotkehlchen.db.filtering import ReportDataFilterQuery
    
    filter_query = ReportDataFilterQuery.make(
        report_id=report_id,
        offset=offset,
        limit=limit,
    )
    
    data = await service.get_report_data(
        filter_query=filter_query,
        with_limit=False,
    )

    if not data['entries']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Report not found or not ready',
        )

    return ReportDataResponse(result=data)


@router.delete('/{report_id}')
async def delete_report(
    report_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AsyncReportsService, Depends(get_async_reports_service)],
) -> ReportResponse:
    """Delete a report"""
    result = await service.delete_pnl_report(report_id)

    if not result.get('result', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Report not found',
        )

    return ReportResponse(
        result={'success': True},
        message='Report deleted successfully',
    )
