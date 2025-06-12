"""Data router for import/export and database management endpoints"""
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.data import DataService
from rotkehlchen.api.v2.services.database import DatabaseService

router = APIRouter()


class ImportRequest(BaseModel):
    """Request model for data import"""
    source: str = "rotki"  # rotki, cointracking, crypto.com, etc.
    filepath: str | None = None
    timestamp_format: str | None = None


class ExportRequest(BaseModel):
    """Request model for data export"""
    directory_path: str | None = None


class DataResponse(BaseModel):
    """Response model for data operations"""
    result: dict[str, Any]
    message: str = ''


def get_data_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> DataService:
    """Get data service instance"""
    return DataService(db_service)


@router.post('/import')
async def import_data(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DataService, Depends(get_data_service)],
    file: UploadFile = File(...),
    source: str = "rotki",
) -> DataResponse:
    """Import data from file"""
    try:
        # Read file content
        content = await file.read()
        
        # Process based on source type
        if source == "rotki":
            # Import rotki JSON data
            data = json.loads(content)
            result = service.import_rotki_data(data)
        elif source == "cointracking":
            # Import CSV data from CoinTracking
            result = service.import_cointracking_csv(content.decode('utf-8'))
        elif source == "cryptocom":
            # Import Crypto.com CSV
            result = service.import_cryptocom_csv(content.decode('utf-8'))
        else:
            raise ValueError(f"Unsupported import source: {source}")
        
        return DataResponse(
            result=result,
            message=f'Data imported successfully from {source}',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Import failed: {str(e)}',
        ) from e


@router.post('/export')
async def export_data(
    request: ExportRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DataService, Depends(get_data_service)],
) -> DataResponse:
    """Export user data"""
    try:
        export_path = service.export_user_data(
            directory_path=request.directory_path,
        )
        
        return DataResponse(
            result={'file': export_path},
            message='Data exported successfully',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Export failed: {str(e)}',
        ) from e


@router.get('/database/info')
async def get_database_info(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DataService, Depends(get_data_service)],
) -> DataResponse:
    """Get database information"""
    info = service.get_database_info()
    return DataResponse(result=info)


@router.get('/database/backups')
async def list_backups(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DataService, Depends(get_data_service)],
) -> DataResponse:
    """List available database backups"""
    backups = service.list_backups()
    return DataResponse(result={'backups': backups})


@router.post('/database/backup')
async def create_backup(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DataService, Depends(get_data_service)],
) -> DataResponse:
    """Create a database backup"""
    try:
        backup_path = service.create_backup()
        return DataResponse(
            result={'backup_file': backup_path},
            message='Backup created successfully',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Backup failed: {str(e)}',
        ) from e


@router.post('/database/restore')
async def restore_backup(
    backup_file: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DataService, Depends(get_data_service)],
) -> DataResponse:
    """Restore from a database backup"""
    try:
        service.restore_backup(backup_file)
        return DataResponse(
            result={'success': True},
            message='Database restored successfully',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Restore failed: {str(e)}',
        ) from e