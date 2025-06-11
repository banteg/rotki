"""Note-related models for user database using SQLModel"""

from typing import Optional, TYPE_CHECKING

from sqlalchemy import CHAR, INTEGER, TEXT, Column, ForeignKey
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.types import BooleanType, TimestampType
from rotkehlchen.db.models.user.base import Base

if TYPE_CHECKING:
    from rotkehlchen.db.models.user.enums import Location


class UserNote(Base, table=True):
    """Model for user notes table"""
    __tablename__ = 'user_notes'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    title: str = Field(sa_column=Column(TEXT, nullable=False))
    content: str = Field(sa_column=Column(TEXT, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        )
    )
    last_update_timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    is_pinned: bool = Field(sa_column=Column(BooleanType, nullable=False))

    # Relationships
    location_ref: Optional['Location'] = Relationship()

    def __repr__(self) -> str:
        return f"<UserNote(id={self.identifier}, title='{self.title}')>"