"""Notes service for managing user notes"""
from typing import Any

from sqlmodel import Session

from rotkehlchen.api.v2.repositories.notes import NotesRepository
from rotkehlchen.types import Timestamp


class NotesService:
    """Service for managing user notes"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.notes_repo = NotesRepository(session)

    def get_all_notes(self) -> list[dict[str, Any]]:
        """Get all user notes"""
        notes = self.notes_repo.get_all()

        return [
            {
                'identifier': note.identifier,
                'title': note.title,
                'content': note.content,
                'location': note.location,
                'last_update_timestamp': note.last_update_timestamp,
            }
            for note in notes
        ]

    def create_note(self, title: str, content: str, location: str) -> dict[str, Any]:
        """Create a new note"""
        import time

        note = self.notes_repo.create(
            title=title,
            content=content,
            location=location,
            last_update_timestamp=Timestamp(int(time.time())),
        )

        return {
            'identifier': note.identifier,
            'title': note.title,
            'content': note.content,
            'location': note.location,
            'last_update_timestamp': note.last_update_timestamp,
        }

    def update_note(
        self,
        note_id: int,
        title: str | None = None,
        content: str | None = None,
        location: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an existing note"""
        import time

        note = self.notes_repo.get_by_id(note_id)

        if not note:
            return None

        # Update fields if provided
        update_data = {}
        if title is not None:
            update_data['title'] = title
        if content is not None:
            update_data['content'] = content
        if location is not None:
            update_data['location'] = location

        update_data['last_update_timestamp'] = Timestamp(int(time.time()))

        updated_note = self.notes_repo.update(note_id, **update_data)

        if not updated_note:
            return None

        return {
            'identifier': updated_note.identifier,
            'title': updated_note.title,
            'content': updated_note.content,
            'location': updated_note.location,
            'last_update_timestamp': updated_note.last_update_timestamp,
        }

    def delete_note(self, note_id: int) -> bool:
        """Delete a note"""
        return self.notes_repo.delete(note_id)
