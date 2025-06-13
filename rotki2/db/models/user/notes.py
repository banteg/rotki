"""Note-related models for user database using SQLModel"""


from sqlalchemy import INTEGER, TEXT, CheckConstraint, Column
from sqlmodel import Field

from rotki2.db.models.types import BooleanType, TimestampType
from rotki2.db.models.user.base import Base


class UserNote(Base, table=True):
    """Model for user notes table"""
    __tablename__ = 'user_notes'
    __table_args__ = (
        CheckConstraint('is_pinned IN (0, 1)'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    title: str = Field(sa_column=Column(TEXT, nullable=False))
    content: str = Field(sa_column=Column(TEXT, nullable=False))
    location: str = Field(sa_column=Column(TEXT, nullable=False))
    last_update_timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    is_pinned: bool = Field(sa_column=Column(BooleanType, nullable=False))

    def __repr__(self) -> str:
        return f"<UserNote(id={self.identifier}, title='{self.title}')>"
