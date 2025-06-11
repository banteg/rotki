"""ENS-related models for user database using SQLModel"""

from typing import Optional

from sqlalchemy import TEXT, UniqueConstraint, Column
from sqlmodel import Field

from rotkehlchen.db.models.types import TimestampType
from rotkehlchen.db.models.user.base import Base


class ENSMapping(Base, table=True):
    """Model for ENS mappings table"""
    __tablename__ = 'ens_mappings'

    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    ens_name: Optional[str] = Field(default=None, sa_column=Column(TEXT, unique=True))
    last_update: int = Field(sa_column=Column(TimestampType, nullable=False))
    last_avatar_update: int = Field(sa_column=Column(TimestampType, nullable=False, server_default='0'))

    def __repr__(self) -> str:
        return f"<ENSMapping(address='{self.address}', ens_name='{self.ens_name}')>"