"""Messages router for managing user messages"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import get_rotkehlchen, require_logged_in_user

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

router = APIRouter()


class MessagesResponse(BaseModel):
    """Response model for messages operations"""
    result: list[dict[str, Any]]
    message: str = ''


class MessageModel(BaseModel):
    """Message data model"""
    id: str
    message: str
    level: str  # 'info', 'warning', 'error'
    timestamp: int
    read: bool = False


@router.get('/', response_model=MessagesResponse)
async def get_messages(
    _: Annotated[str, Depends(require_logged_in_user)],
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> MessagesResponse:
    """Get all messages for the user"""
    # In a real implementation, this would fetch from a message queue or database
    # For now, return empty list or sample messages
    
    messages = []
    
    # Check if there are any pending updates
    from rotkehlchen.utils.version_check import get_current_version
    version_info = get_current_version()
    
    # Add sample messages based on system state
    if hasattr(rotkehlchen, 'task_manager') and rotkehlchen.task_manager:
        # Check for running tasks
        running_tasks = rotkehlchen.task_manager.get_running_tasks()
        if running_tasks:
            messages.append({
                'id': 'task_running',
                'message': f'{len(running_tasks)} background tasks are currently running',
                'level': 'info',
                'timestamp': int(time.time()),
                'read': False,
            })
    
    return MessagesResponse(result=messages)


@router.post('/', response_model=MessagesResponse)
async def get_messages_post(
    _: Annotated[str, Depends(require_logged_in_user)],
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> MessagesResponse:
    """Get all messages for the user (POST version)"""
    return await get_messages(_, rotkehlchen)


@router.post('/{message_id}/read', response_model=MessagesResponse)
async def mark_message_read(
    message_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
) -> MessagesResponse:
    """Mark a message as read"""
    # In a real implementation, this would update the message status
    return MessagesResponse(
        result=[],
        message=f'Message {message_id} marked as read',
    )


import time