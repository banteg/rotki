"""Trading-related models for user database using SQLModel"""


from sqlalchemy import CHAR, TEXT, Column, ForeignKey
from sqlmodel import Field

from rotkehlchen.db.models.types import TimestampType
from rotkehlchen.db.models.user.base import Base


class MarginPosition(Base, table=True):
    """Model for margin positions table"""
    __tablename__ = 'margin_positions'

    id: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        ),
    )
    open_time: int | None = Field(default=None, sa_column=Column(TimestampType, nullable=True))
    close_time: int | None = Field(default=None, sa_column=Column(TimestampType, nullable=True))
    profit_loss: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    pl_currency: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        ),
    )
    fee: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    fee_currency: str | None = Field(
        default=None,
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=True,
        ),
    )
    link: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    notes: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

    def __repr__(self) -> str:
        return f"<MarginPosition(id={self.id}, location='{self.location}')>"
