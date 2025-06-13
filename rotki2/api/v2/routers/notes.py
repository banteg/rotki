"""Notes router for managing user notes"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from rotki2.api.v2.dependencies import get_db_session, require_logged_in_user
from rotki2.api.v2.services.notes import NotesService
from rotkehlchen.types import Timestamp

router = APIRouter()


class NoteModel(BaseModel):
    """Note data model"""
    identifier: int | None = None
    title: str
    content: str
    location: str
    last_update_timestamp: Timestamp


class NotesResponse(BaseModel):
    """Response model for notes operations"""
    result: list[dict[str, Any]] | dict[str, Any]
    message: str = ''


class NoteCreateRequest(BaseModel):
    """Request model for creating a note"""
    title: str
    content: str
    location: str


class NoteUpdateRequest(BaseModel):
    """Request model for updating a note"""
    title: str | None = None
    content: str | None = None
    location: str | None = None


def get_notes_service(session: Session) -> NotesService:
    """Get notes service instance"""
    return NotesService(session)


@router.get('/', response_model=NotesResponse)
async def get_notes(
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> NotesResponse:
    """Get all user notes"""
    service = get_notes_service(session)
    notes = service.get_all_notes()

    return NotesResponse(result=notes)


@router.post('/', response_model=NotesResponse)
async def create_note(
    note_data: NoteCreateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> NotesResponse:
    """Create a new note"""
    service = get_notes_service(session)

    note = service.create_note(
        title=note_data.title,
        content=note_data.content,
        location=note_data.location,
    )

    return NotesResponse(
        result=note,
        message='Note created successfully',
    )


@router.put('/{note_id}', response_model=NotesResponse)
async def update_note(
    note_id: int,
    note_update: NoteUpdateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> NotesResponse:
    """Update an existing note"""
    service = get_notes_service(session)

    note = service.update_note(
        note_id=note_id,
        title=note_update.title,
        content=note_update.content,
        location=note_update.location,
    )

    if not note:
        raise HTTPException(
            status_code=404,
            detail=f'Note with id {note_id} not found',
        )

    return NotesResponse(
        result=note,
        message='Note updated successfully',
    )


@router.delete('/{note_id}', response_model=NotesResponse)
async def delete_note(
    note_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> NotesResponse:
    """Delete a note"""
    service = get_notes_service(session)

    success = service.delete_note(note_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f'Note with id {note_id} not found',
        )

    return NotesResponse(
        result={},
        message='Note deleted successfully',
    )
