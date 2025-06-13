"""Snapshots router for managing database snapshots"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.snapshots import SnapshotsService
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
            detail=f'Failed to create snapshot: {str(e)}',
        ) from e


@router.get('/{timestamp}')
async def get_snapshot(
    _: Annotated[str, Depends(require_logged_in_user)],
    snapshots: Annotated[SnapshotsService, Depends(get_snapshots_service)],
    timestamp: int = Path(..., description="Timestamp of the snapshot"),
) -> SnapshotsResponse:
    """Get a specific snapshot by timestamp"""
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
    timestamp: int = Path(..., description="Timestamp of the snapshot"),
) -> SnapshotsResponse:
    """Delete a snapshot"""
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
    timestamp: int = Path(..., description="Timestamp of the snapshot"),
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
            detail=f'Failed to restore snapshot: {str(e)}',
        ) from e