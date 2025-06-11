"""Cache-related models for user database using SQLModel"""

from typing import Optional

from sqlalchemy import TEXT, VARCHAR, UniqueConstraint, Column
from sqlmodel import Field

from rotkehlchen.db.orm.types import TimestampType
from rotkehlchen.db.orm.userdb.base import Base


class UsedQueryRange(Base, table=True):
    """Model for used query ranges table"""
    __tablename__ = 'used_query_ranges'

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    start_ts: Optional[int] = Field(default=None, sa_column=Column(TimestampType))
    end_ts: Optional[int] = Field(default=None, sa_column=Column(TimestampType))

    def __repr__(self) -> str:
        return f"<UsedQueryRange(name='{self.name}', start={self.start_ts}, end={self.end_ts})>"


class KeyValueCache(Base, table=True):
    """Model for key value cache table"""
    __tablename__ = 'key_value_cache'

    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    last_queried_ts: int = Field(sa_column=Column(TimestampType, nullable=False))

    def __repr__(self) -> str:
        return f"<KeyValueCache(name='{self.name}')>"


class MultiSettings(Base, table=True):
    """Model for multisettings table"""
    __tablename__ = 'multisettings'
    __table_args__ = (
        UniqueConstraint('name', 'value'),
    )

    # SQLAlchemy requires a primary key, but the SQL doesn't define one
    # Using composite primary key as the closest match to UNIQUE(name, value)
    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False, server_default=''))

    def __repr__(self) -> str:
        return f"<MultiSettings(name='{self.name}', value='{self.value}')>"