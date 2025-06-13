"""Actions router for managing ignored actions"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.actions import ActionsService

router = APIRouter()


class ActionsResponse(BaseModel):
    """Response model for actions operations"""
    result: dict[str, Any]
    message: str = ''


class IgnoredActionsRequest(BaseModel):
    """Request model for managing ignored actions"""
    action_type: str
    action_ids: list[str]


def get_actions_service() -> ActionsService:
    """Get actions service instance"""
    return ActionsService()


@router.get('/ignored')
async def get_ignored_actions(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ActionsService, Depends(get_actions_service)],
) -> ActionsResponse:
    """Get all ignored actions"""
    ignored = service.get_ignored_actions()
    
    return ActionsResponse(result={'ignored_actions': ignored})


@router.post('/ignored')
async def add_ignored_actions(
    request_data: IgnoredActionsRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ActionsService, Depends(get_actions_service)],
) -> ActionsResponse:
    """Add actions to ignore list"""
    try:
        added = service.add_ignored_actions(
            action_type=request_data.action_type,
            action_ids=request_data.action_ids,
        )
        
        return ActionsResponse(
            result={'added': added},
            message=f'Added {added} actions to ignore list',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# v1 compatibility endpoints
@router.put('/ignored')
async def add_ignored_actions_v1(
    action_type: str,
    action_ids: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ActionsService, Depends(get_actions_service)],
) -> ActionsResponse:
    """Add action IDs to ignored list - Compatible with v1 PUT /api/1/actions/ignored"""
    try:
        added = service.add_ignored_actions(
            action_type=action_type,
            action_ids=action_ids,
        )
        
        return ActionsResponse(
            result={'ignored_actions': added},
            message=f'Added {len(action_ids)} actions to ignore list',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/ignored')
async def remove_ignored_actions_v1(
    action_type: str,
    action_ids: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ActionsService, Depends(get_actions_service)],
) -> ActionsResponse:
    """Remove action IDs from ignored list - Compatible with v1 DELETE /api/1/actions/ignored"""
    try:
        removed = service.remove_ignored_actions(
            action_type=action_type,
            action_ids=action_ids,
        )
        
        return ActionsResponse(
            result={'removed': removed},
            message=f'Removed {removed} actions from ignore list',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/ignored')
async def remove_ignored_actions(
    request_data: IgnoredActionsRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ActionsService, Depends(get_actions_service)],
) -> ActionsResponse:
    """Remove actions from ignore list"""
    try:
        removed = service.remove_ignored_actions(
            action_type=request_data.action_type,
            action_ids=request_data.action_ids,
        )
        
        return ActionsResponse(
            result={'removed': removed},
            message=f'Removed {removed} actions from ignore list',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# v1 compatibility endpoints
@router.put('/ignored')
async def add_ignored_actions_v1(
    action_type: str,
    action_ids: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ActionsService, Depends(get_actions_service)],
) -> ActionsResponse:
    """Add action IDs to ignored list - Compatible with v1 PUT /api/1/actions/ignored"""
    try:
        added = service.add_ignored_actions(
            action_type=action_type,
            action_ids=action_ids,
        )
        
        return ActionsResponse(
            result={'ignored_actions': added},
            message=f'Added {len(action_ids)} actions to ignore list',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/ignored')
async def remove_ignored_actions_v1(
    action_type: str,
    action_ids: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ActionsService, Depends(get_actions_service)],
) -> ActionsResponse:
    """Remove action IDs from ignored list - Compatible with v1 DELETE /api/1/actions/ignored"""
    try:
        removed = service.remove_ignored_actions(
            action_type=action_type,
            action_ids=action_ids,
        )
        
        return ActionsResponse(
            result={'removed': removed},
            message=f'Removed {removed} actions from ignore list',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e