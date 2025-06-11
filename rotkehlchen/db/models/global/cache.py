"""Cache-related models for global database using SQLModel"""

from typing import Optional

from sqlalchemy import CHAR, INTEGER, TEXT, Column, ForeignKey
from sqlmodel import Field

from rotkehlchen.db.orm.types import FValType, TimestampType
from rotkehlchen.db.models.global.base import Base


class PriceHistory(Base, table=True):
    """Model for price history table"""
    __tablename__ = 'price_history'

    from_asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    to_asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    source_type: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('price_history_source_types.type'),
            primary_key=True,
            nullable=False,
        )
    )
    timestamp: int = Field(sa_column=Column(TimestampType, primary_key=True, nullable=False))
    price: str = Field(sa_column=Column(FValType, nullable=False))

    def __repr__(self) -> str:
        return f"<PriceHistory(from='{self.from_asset}', to='{self.to_asset}', time={self.timestamp})>"


class GeneralCache(Base, table=True):
    """Model for general cache table"""
    __tablename__ = 'general_cache'

    key: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    last_queried_ts: int = Field(sa_column=Column(TimestampType, nullable=False))

    def __repr__(self) -> str:
        return f"<GeneralCache(key='{self.key}')>"


class UniqueCache(Base, table=True):
    """Model for unique cache table"""
    __tablename__ = 'unique_cache'

    key: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    last_queried_ts: int = Field(sa_column=Column(TimestampType, nullable=False))

    def __repr__(self) -> str:
        return f"<UniqueCache(key='{self.key}')>"