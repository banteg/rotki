"""Cache-related models for user database using SQLModel"""


from sqlalchemy import TEXT, VARCHAR, Column
from sqlmodel import Field

from rotkehlchen.db.models.types import TimestampType
from rotkehlchen.db.models.user.base import Base


class UsedQueryRange(Base, table=True):
    """Model for used query ranges table"""
    __tablename__ = 'used_query_ranges'

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    start_ts: int | None = Field(default=None, sa_column=Column(TimestampType))
    end_ts: int | None = Field(default=None, sa_column=Column(TimestampType))

    def __repr__(self) -> str:
        return f"<UsedQueryRange(name='{self.name}', start={self.start_ts}, end={self.end_ts})>"


class KeyValueCache(Base, table=True):
    """Model for key value cache table"""
    __tablename__ = 'key_value_cache'

    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    value: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

    def __repr__(self) -> str:
        return f"<KeyValueCache(name='{self.name}')>"


class MultiSettings(Base, table=True):
    """Model for multisettings table"""
    __tablename__ = 'multisettings'
    # Note: The original SQL table doesn't have a primary key,
    # but we use the UNIQUE constraint columns as a composite primary key
    # to satisfy SQLAlchemy's requirements

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    value: str | None = Field(default=None, sa_column=Column(TEXT, primary_key=True, nullable=False))

    def __repr__(self) -> str:
        return f"<MultiSettings(name='{self.name}', value='{self.value}')>"
