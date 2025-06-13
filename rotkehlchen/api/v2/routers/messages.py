"""Messages router for managing user messages"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import get_rotkehlchen, require_logged_in_user
from rotkehlchen.api.v2.services.messages import MessagesService

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

router = APIRouter()


class MessagesResponse(BaseModel):
    """Response model for messages operations"""
    result: list[dict[str, Any]] | dict[str, Any]
    message: str = ''


class MessageModel(BaseModel):
    """Message data model"""
    id: str
    message: str
    level: str  # 'info', 'warning', 'error'
    timestamp: int
    read: bool = False


def get_messages_service(rotkehlchen: 'Rotkehlchen | None' = None) -> MessagesService:
    """Get messages service instance"""
    return MessagesService(rotkehlchen)


@router.get('/', response_model=MessagesResponse)
async def get_messages(
    _: Annotated[str, Depends(require_logged_in_user)],
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
    unread_only: bool = False,
) -> MessagesResponse:
    """Get all messages for the user"""
    service = get_messages_service(rotkehlchen)
    messages = service.get_all_messages(unread_only=unread_only)

    return MessagesResponse(result=messages)


@router.post('/', response_model=MessagesResponse)
async def get_messages_post(
    _: Annotated[str, Depends(require_logged_in_user)],
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
    unread_only: bool = False,
) -> MessagesResponse:
    """Get all messages for the user (POST version)"""
    return await get_messages(_, rotkehlchen, unread_only)


@router.post('/{message_id}/read', response_model=MessagesResponse)
async def mark_message_read(
    message_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> MessagesResponse:
    """Mark a message as read"""
    service = get_messages_service(rotkehlchen)
    success = service.mark_message_read(message_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Message {message_id} not found',
        )

    return MessagesResponse(
        result={'success': True},
        message=f'Message {message_id} marked as read',
    )
