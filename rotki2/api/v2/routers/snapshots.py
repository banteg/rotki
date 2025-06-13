"""Snapshots router for managing database snapshots"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.snapshots import SnapshotsService
from rotkehlchen.types import Timestamp

router = APIRouter()


class SnapshotsResponse(BaseModel):
    """Response model for snapshots operations"""
    result: dict[str, Any] | list[dict[str, Any]]
    message: str = ''


class SnapshotRequest(BaseModel):
    """Request model for creating a snapshot"""
    name: str | None = None
    description: str | None = None


class SnapshotImportRequest(BaseModel):
    """Request model for importing snapshot via file path"""
    path: str
    password: str | None = None


class SnapshotEditRequest(BaseModel):
    """Request model for editing snapshot metadata"""
    name: str | None = None
    description: str | None = None


def get_snapshots_service() -> SnapshotsService:
    """Get snapshots service instance"""
    return SnapshotsService()


@router.get('/')
async def get_snapshots(
    _: Annotated[str, Depends(require_logged_in_user)],
    snapshots: Annotated[SnapshotsService, Depends(get_snapshots_service)],
) -> SnapshotsResponse:
    """Get all database snapshots"""
    snapshots_list = snapshots.get_all_snapshots()

    return SnapshotsResponse(result=snapshots_list)


@router.post('/')
async def create_snapshot(
    snapshot_data: SnapshotRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    snapshots: Annotated[SnapshotsService, Depends(get_snapshots_service)],
) -> SnapshotsResponse:
    """Create a new database snapshot"""
    try:
        snapshot_info = snapshots.create_snapshot(
            name=snapshot_data.name,
            description=snapshot_data.description,
        )

        return SnapshotsResponse(
            result=snapshot_info,
            message='Snapshot created successfully',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to create snapshot: {e!s}',
        ) from e


@router.get('/{timestamp}')
async def get_snapshot(
    _: Annotated[str, Depends(require_logged_in_user)],
    snapshots: Annotated[SnapshotsService, Depends(get_snapshots_service)],
    timestamp: int = Path(..., description='Timestamp of the snapshot'),
) -> SnapshotsResponse:
    """Get a DB snapshot - Compatible with v1 GET /api/1/snapshots/<int:timestamp>"""
    snapshot = snapshots.get_snapshot(Timestamp(timestamp))

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Snapshot not found',
        )

    return SnapshotsResponse(result=snapshot)


@router.delete('/{timestamp}')
async def delete_snapshot(
    _: Annotated[str, Depends(require_logged_in_user)],
    snapshots: Annotated[SnapshotsService, Depends(get_snapshots_service)],
    timestamp: int = Path(..., description='Timestamp of the snapshot'),
) -> SnapshotsResponse:
    """Delete a DB snapshot - Compatible with v1 DELETE /api/1/snapshots/<int:timestamp>"""
    success = snapshots.delete_snapshot(Timestamp(timestamp))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Snapshot not found',
        )

    return SnapshotsResponse(
        result={'success': True},
        message='Snapshot deleted successfully',
    )


@router.put('/{timestamp}')
async def restore_snapshot(
    _: Annotated[str, Depends(require_logged_in_user)],
    snapshots: Annotated[SnapshotsService, Depends(get_snapshots_service)],
    timestamp: int = Path(..., description='Timestamp of the snapshot'),
) -> SnapshotsResponse:
    """Restore from a snapshot"""
    try:
        success = snapshots.restore_snapshot(Timestamp(timestamp))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Snapshot not found',
            )

        return SnapshotsResponse(
            result={'success': True},
            message='Snapshot restored successfully',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to restore snapshot: {e!s}',
        ) from e


# v1 compatibility endpoints
@router.put('/')
async def import_snapshot_via_path(
    request_data: SnapshotImportRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[SnapshotsService, Depends(get_snapshots_service)],
) -> SnapshotsResponse:
    """Import a DB snapshot via file paths - Compatible with v1 PUT /api/1/snapshots"""
    try:
        result = service.import_snapshot_from_path(
            path=request_data.path,
            password=request_data.password,
        )

        return SnapshotsResponse(
            result=result,
            message='Snapshot imported successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post('/')
async def import_snapshot_via_upload(
    file: UploadFile = File(...),
    password: str | None = Form(None),
    _: Annotated[str, Depends(require_logged_in_user)] = None,
    service: Annotated[SnapshotsService, Depends(get_snapshots_service)] = None,
) -> SnapshotsResponse:
    """Import a DB snapshot via file upload - Compatible with v1 POST /api/1/snapshots"""
    try:
        # Read file content
        content = await file.read()

        result = service.import_snapshot_from_upload(
            content=content,
            filename=file.filename,
            password=password,
        )

        return SnapshotsResponse(
            result=result,
            message='Snapshot imported successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.patch('/{timestamp}')
async def edit_snapshot(
    timestamp: int,
    request_data: SnapshotEditRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[SnapshotsService, Depends(get_snapshots_service)],
) -> SnapshotsResponse:
    """Edit a DB snapshot - Compatible with v1 PATCH /api/1/snapshots/<int:timestamp>"""
    try:
        result = service.edit_snapshot(
            timestamp=Timestamp(timestamp),
            name=request_data.name,
            description=request_data.description,
        )

        if result:
            return SnapshotsResponse(
                result={'success': True},
                message='Snapshot updated successfully',
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Snapshot with timestamp {timestamp} not found',
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
