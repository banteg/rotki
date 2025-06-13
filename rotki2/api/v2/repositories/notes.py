"""Repository for managing user notes"""
from typing import Any

from sqlmodel import select

from rotki2.api.v2.repositories.base import BaseRepository
from rotki2.db.models.user.notes import UserNote
from rotkehlchen.types import Timestamp


class NotesRepository(BaseRepository[UserNote]):
    """Repository for managing user notes"""

    model = UserNote

    def get_all(self) -> list[UserNote]:
        """Get all notes ordered by last update timestamp"""
        query = select(self.model).order_by(self.model.last_update_timestamp.desc())
        return list(self.session.exec(query).all())

    def get_by_id(self, note_id: int) -> UserNote | None:
        """Get a note by ID"""
        query = select(self.model).where(self.model.identifier == note_id)
        return self.session.exec(query).first()

    def create(
        self,
        title: str,
        content: str,
        location: str,
        last_update_timestamp: Timestamp,
    ) -> UserNote:
        """Create a new note"""
        note = self.model(
            title=title,
            content=content,
            location=location,
            last_update_timestamp=last_update_timestamp,
        )

        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)

        return note

    def update(self, note_id: int, **kwargs: Any) -> UserNote | None:
        """Update a note"""
        note = self.get_by_id(note_id)

        if not note:
            return None

        for key, value in kwargs.items():
            setattr(note, key, value)

        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)

        return note

    def delete(self, note_id: int) -> bool:
        """Delete a note"""
        note = self.get_by_id(note_id)

        if not note:
            return False

        self.session.delete(note)
        self.session.commit()

        return True
