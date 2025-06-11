"""Trading-related models for user database using SQLModel"""

from typing import Optional

from sqlalchemy import CHAR, INTEGER, TEXT, Column, ForeignKey
from sqlmodel import Field

from rotkehlchen.db.orm.types import FValType, TimestampType
from rotkehlchen.db.orm.userdb.base import Base


class MarginPosition(Base, table=True):
    """Model for margin positions table"""
    __tablename__ = 'margin_positions'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        )
    )
    open_time: int = Field(sa_column=Column(TimestampType, nullable=False))
    close_time: int = Field(sa_column=Column(TimestampType, nullable=False))
    profit_loss: str = Field(sa_column=Column(FValType, nullable=False))
    pl_currency: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    fee: str = Field(sa_column=Column(FValType, nullable=False))
    fee_currency: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    link: str = Field(sa_column=Column(TEXT, nullable=False))
    notes: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<MarginPosition(id={self.id}, location='{self.location}')>"