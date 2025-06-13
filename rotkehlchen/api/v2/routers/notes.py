"""Notes router for managing user notes"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from rotkehlchen.api.v2.dependencies import get_db_session, require_logged_in_user
from rotkehlchen.db.models.user_note import UserNote
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    pass

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


@router.get('/', response_model=NotesResponse)
async def get_notes(
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> NotesResponse:
    """Get all user notes"""
    query = select(UserNote).order_by(UserNote.last_update_timestamp.desc())
    notes = session.exec(query).all()
    
    result = [
        {
            'identifier': note.identifier,
            'title': note.title,
            'content': note.content,
            'location': note.location,
            'last_update_timestamp': note.last_update_timestamp,
        }
        for note in notes
    ]
    
    return NotesResponse(result=result)


@router.post('/', response_model=NotesResponse)
async def create_note(
    note_data: NoteCreateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> NotesResponse:
    """Create a new note"""
    import time
    
    note = UserNote(
        title=note_data.title,
        content=note_data.content,
        location=note_data.location,
        last_update_timestamp=Timestamp(int(time.time())),
    )
    
    session.add(note)
    session.commit()
    session.refresh(note)
    
    result = {
        'identifier': note.identifier,
        'title': note.title,
        'content': note.content,
        'location': note.location,
        'last_update_timestamp': note.last_update_timestamp,
    }
    
    return NotesResponse(
        result=result,
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
    import time
    
    query = select(UserNote).where(UserNote.identifier == note_id)
    note = session.exec(query).first()
    
    if not note:
        raise HTTPException(
            status_code=404,
            detail=f'Note with id {note_id} not found',
        )
    
    # Update fields if provided
    if note_update.title is not None:
        note.title = note_update.title
    if note_update.content is not None:
        note.content = note_update.content
    if note_update.location is not None:
        note.location = note_update.location
    
    note.last_update_timestamp = Timestamp(int(time.time()))
    
    session.add(note)
    session.commit()
    session.refresh(note)
    
    result = {
        'identifier': note.identifier,
        'title': note.title,
        'content': note.content,
        'location': note.location,
        'last_update_timestamp': note.last_update_timestamp,
    }
    
    return NotesResponse(
        result=result,
        message='Note updated successfully',
    )


@router.delete('/{note_id}', response_model=NotesResponse)
async def delete_note(
    note_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> NotesResponse:
    """Delete a note"""
    query = select(UserNote).where(UserNote.identifier == note_id)
    note = session.exec(query).first()
    
    if not note:
        raise HTTPException(
            status_code=404,
            detail=f'Note with id {note_id} not found',
        )
    
    session.delete(note)
    session.commit()
    
    return NotesResponse(
        result={},
        message='Note deleted successfully',
    )