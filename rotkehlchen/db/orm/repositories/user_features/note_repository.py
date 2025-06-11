"""Repository for user notes management"""

from typing import Optional

from sqlalchemy import delete, func, or_, select

from rotkehlchen.db.orm.models import UserNote
from rotkehlchen.db.orm.repositories.base import BaseRepository


class UserNoteRepository(BaseRepository[UserNote]):
    """Repository for managing user notes"""
    
    def __init__(self, session):
        super().__init__(session, UserNote)
    
    def add_note(
        self,
        title: str,
        content: str,
        location: str,
        last_update_timestamp: int,
    ) -> UserNote:
        """Add a user note"""
        note = UserNote(
            title=title,
            content=content,
            location=location,
            last_update_timestamp=last_update_timestamp,
        )
        return self.add(note)
    
    def get_note(self, identifier: int) -> Optional[UserNote]:
        """Get a note by identifier"""
        return self.get(identifier=identifier)
    
    def get_notes(
        self,
        location: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[UserNote]:
        """Get all notes with optional filtering"""
        query = select(UserNote)
        
        if location:
            query = query.filter_by(location=location)
        
        # Order by last update timestamp descending
        query = query.order_by(UserNote.last_update_timestamp.desc())
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        
        return list(self.session.execute(query).scalars().all())
    
    def update_note(
        self,
        identifier: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        location: Optional[str] = None,
        last_update_timestamp: Optional[int] = None,
    ) -> Optional[UserNote]:
        """Update a user note"""
        note = self.get_note(identifier)
        if not note:
            return None
        
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if location is not None:
            note.location = location
        if last_update_timestamp is not None:
            note.last_update_timestamp = last_update_timestamp
        
        return self.update(note)
    
    def delete_note(self, identifier: int) -> bool:
        """Delete a user note"""
        return self.delete_by(identifier=identifier) > 0
    
    def search_notes(
        self,
        search_term: str,
        in_title: bool = True,
        in_content: bool = True,
    ) -> list[UserNote]:
        """Search notes by title and/or content"""
        query = select(UserNote)
        
        search_pattern = f'%{search_term}%'
        conditions = []
        
        if in_title:
            conditions.append(UserNote.title.like(search_pattern))
        if in_content:
            conditions.append(UserNote.content.like(search_pattern))
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        return list(self.session.execute(query).scalars().all())
    
    def get_notes_count(self, location: Optional[str] = None) -> int:
        """Get count of notes"""
        query = select(func.count()).select_from(UserNote)
        
        if location:
            query = query.filter_by(location=location)
        
        return self.session.execute(query).scalar() or 0
    
    def get_latest_note(self) -> Optional[UserNote]:
        """Get the most recently updated note"""
        stmt = select(UserNote).order_by(
            UserNote.last_update_timestamp.desc()
        ).limit(1)
        
        return self.session.execute(stmt).scalar_one_or_none()
    
    def delete_notes_by_location(self, location: str) -> int:
        """Delete all notes for a specific location"""
        stmt = delete(UserNote).filter_by(location=location)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount