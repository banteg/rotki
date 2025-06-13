"""Import/Export router for data import and export operations"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.import_export import ImportExportService

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


def get_import_export_service() -> ImportExportService:
    """Get import/export service instance"""
    return ImportExportService()


@router.get('/')
async def get_importers(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> ImportExportResponse:
    """Get available data importers"""
    importers = service.get_available_importers()
    
    return ImportExportResponse(result={'importers': importers})


@router.post('/')
async def import_data(
    import_data: ImportRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> ImportExportResponse:
    """Import data from external source"""
    try:
        result = service.import_data(
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
        
        result = service.import_from_file(
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