"""Reports router for accounting and tax report endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import (
    get_accountant,
    get_database_service,
    get_rotki_notifier,
    require_logged_in_user,
)
from rotki2.api.v2.services.database import DatabaseService
from rotki2.api.v2.services.reports import ReportsService
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


def get_reports_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    accountant: Annotated['Accountant', Depends(get_accountant)],
    notifier: Annotated['RotkiNotifier', Depends(get_rotki_notifier)],
) -> ReportsService:
    """Get reports service instance"""
    return ReportsService(
        db_service=db_service,
        accountant=accountant,
        notifier=notifier,
    )


@router.post('/')
async def generate_report(
    request: ReportGenerateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ReportsService, Depends(get_reports_service)],
) -> ReportResponse:
    """Generate a new accounting report"""
    try:
        report_id = service.generate_report(
            from_timestamp=request.from_timestamp,
            to_timestamp=request.to_timestamp,
            report_name=request.report_name,
        )

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
    service: Annotated[ReportsService, Depends(get_reports_service)],
) -> ReportResponse:
    """List all available reports"""
    reports = service.list_reports()
    return ReportResponse(result={'reports': reports})


@router.get('/{report_id}')
async def get_report(
    report_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ReportsService, Depends(get_reports_service)],
) -> ReportResponse:
    """Get report status and metadata"""
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Report not found',
        )

    return ReportResponse(result=report)


@router.get('/{report_id}/data')
async def get_report_data(
    report_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ReportsService, Depends(get_reports_service)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, gt=0, le=5000),
) -> ReportDataResponse:
    """Get report data (events, trades, etc.)"""
    data = service.get_report_data(
        report_id=report_id,
        offset=offset,
        limit=limit,
    )

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Report not found or not ready',
        )

    return ReportDataResponse(result=data)


@router.delete('/{report_id}')
async def delete_report(
    report_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ReportsService, Depends(get_reports_service)],
) -> ReportResponse:
    """Delete a report"""
    success = service.delete_report(report_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Report not found',
        )

    return ReportResponse(
        result={'success': True},
        message='Report deleted successfully',
    )
