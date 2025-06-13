"""Import/Export router for data import and export operations"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.dependencies import get_async_session, require_logged_in_user
from rotki2.api.v2.services.import_export import ImportExportService

router = APIRouter()


class ImportExportResponse(BaseModel):
    """Response model for import/export operations"""
    result: dict[str, Any]
    message: str = ''


class ImportRequest(BaseModel):
    """Request model for importing data"""
    source: str  # 'cointracking', 'cryptocom', 'blockfi', 'nexo', etc.
    data: dict[str, Any] | None = None
    file_path: str | None = None


class RestoreRequest(BaseModel):
    """Request model for restoring backup"""
    backup_file: str


async def get_import_export_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ImportExportService:
    """Get import/export service instance"""
    return ImportExportService(session=session)


@router.get('/')
async def get_importers(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> ImportExportResponse:
    """Get available data importers"""
    importers = await service.get_available_importers()

    return ImportExportResponse(result={'importers': importers})


@router.post('/')
async def import_data(
    import_data: ImportRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> ImportExportResponse:
    """Import data from external source"""
    try:
        result = await service.import_data(
            source=import_data.source,
            data=import_data.data,
            file_path=import_data.file_path,
        )

        return ImportExportResponse(
            result=result,
            message=f'Successfully imported data from {import_data.source}',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post('/file')
async def import_file(
    file: UploadFile = File(...),
    source: str = 'auto',
    _: Annotated[str, Depends(require_logged_in_user)] = None,
    service: Annotated[ImportExportService, Depends(get_import_export_service)] = None,
) -> ImportExportResponse:
    """Import data from uploaded file"""
    try:
        # Read file content
        content = await file.read()

        result = await service.import_from_file(
            filename=file.filename,
            content=content,
            source=source,
        )

        return ImportExportResponse(
            result=result,
            message=f'Successfully imported data from {file.filename}',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get('/export')
async def export_data(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
    directory_path: str | None = None,
) -> ImportExportResponse:
    """Export user data to JSON file"""
    try:
        # Use DataService for export if available
        if service.data_service:
            filepath = await service.data_service.export_user_data(directory_path)
            return ImportExportResponse(
                result={'filepath': filepath},
                message='Data exported successfully',
            )
        else:
            raise ValueError('Export service not available')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get('/database/info')
async def get_database_info(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> ImportExportResponse:
    """Get database information"""
    try:
        if service.data_service:
            info = await service.data_service.get_database_info()
            return ImportExportResponse(result=info)
        else:
            raise ValueError('Database info service not available')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get('/backups')
async def list_backups(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> ImportExportResponse:
    """List available database backups"""
    try:
        if service.data_service:
            backups = await service.data_service.list_backups()
            return ImportExportResponse(result={'backups': backups})
        else:
            raise ValueError('Backup service not available')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post('/backups')
async def create_backup(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> ImportExportResponse:
    """Create a database backup"""
    try:
        if service.data_service:
            backup_path = await service.data_service.create_backup()
            return ImportExportResponse(
                result={'backup_path': backup_path},
                message='Backup created successfully',
            )
        else:
            raise ValueError('Backup service not available')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post('/backups/restore')
async def restore_backup(
    restore_data: RestoreRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> ImportExportResponse:
    """Restore from a database backup"""
    try:
        if service.data_service:
            await service.data_service.restore_backup(restore_data.backup_file)
            return ImportExportResponse(
                result={'success': True},
                message='Backup restored successfully',
            )
        else:
            raise ValueError('Restore service not available')
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e