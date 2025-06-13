"""Conflict resolution models for user database using SQLModel"""

from sqlalchemy import INTEGER, TEXT, Column
from sqlmodel import Field

from rotki2.db.models.user.base import Base


class UnresolvedRemoteConflict(Base, table=True):
    """Model for unresolved remote conflicts table"""
    __tablename__ = 'unresolved_remote_conflicts'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    local_id: int = Field(sa_column=Column(INTEGER, nullable=False))
    remote_data: str = Field(sa_column=Column(TEXT, nullable=False))
    type: int = Field(sa_column=Column(INTEGER, nullable=False))

    def __repr__(self) -> str:
        return f'<UnresolvedRemoteConflict(id={self.identifier}, type={self.type})>'
