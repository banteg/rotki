"""Calendar-related models for user database using SQLModel"""

from typing import Optional

from sqlalchemy import INTEGER, TEXT, Column, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlmodel import Field, Relationship

from rotki2.db.models.types import BooleanType, TimestampType
from rotki2.db.models.user.base import Base


class Calendar(Base, table=True):
    """Model for calendar table"""
    __tablename__ = 'calendar'
    __table_args__ = (
        UniqueConstraint('name', 'address', 'blockchain'),
        ForeignKeyConstraint(
            ['blockchain', 'address'],
            ['blockchain_accounts.blockchain', 'blockchain_accounts.account'],
            ondelete='CASCADE',
        ),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    name: str = Field(sa_column=Column(TEXT, nullable=False))
    timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(TEXT))
    counterparty: str | None = Field(default=None, sa_column=Column(TEXT))
    address: str | None = Field(default=None, sa_column=Column(TEXT))
    blockchain: str | None = Field(default=None, sa_column=Column(TEXT))
    color: str | None = Field(default=None, sa_column=Column(TEXT))
    auto_delete: bool = Field(sa_column=Column(BooleanType, nullable=False))

    # Relationships
    reminders: list['CalendarReminder'] = Relationship(
        back_populates='calendar_entry',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Calendar(id={self.identifier}, name='{self.name}')>"


class CalendarReminder(Base, table=True):
    """Model for calendar reminders table"""
    __tablename__ = 'calendar_reminders'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    event_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('calendar.identifier', ondelete='CASCADE'),
            nullable=False,
        ),
    )
    secs_before: int = Field(sa_column=Column(INTEGER, nullable=False))
    acknowledged: bool = Field(sa_column=Column(BooleanType, nullable=False, server_default='0'))

    # Relationships
    calendar_entry: Optional['Calendar'] = Relationship(back_populates='reminders')

    def __repr__(self) -> str:
        return f'<CalendarReminder(id={self.identifier}, event_id={self.event_id})>'
