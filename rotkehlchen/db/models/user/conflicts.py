"""Conflict resolution models for user database using SQLModel"""

from sqlalchemy import INTEGER, TEXT, Column
from sqlmodel import Field

from rotkehlchen.db.models.user.base import Base


class UnresolvedRemoteConflict(Base, table=True):
    """Model for unresolved remote conflicts table"""
    __tablename__ = 'unresolved_remote_conflicts'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    local_id: str = Field(sa_column=Column(TEXT, nullable=False))
    remote_id: str = Field(sa_column=Column(TEXT, nullable=False))
    type: str = Field(sa_column=Column(TEXT, nullable=False))
    local_data: str = Field(sa_column=Column(TEXT, nullable=False))
    remote_data: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<UnresolvedRemoteConflict(id={self.id}, type='{self.type}')>"