"""History event models for user database"""

from typing import Optional

from sqlalchemy import BLOB, CHAR, INTEGER, TEXT, Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship

from rotki2.db.models.user.base import Base


class HistoryEvent(Base, table=True):
    """Model for history_events table"""
    __tablename__ = 'history_events'
    __table_args__ = (
        UniqueConstraint('event_identifier', 'sequence_index'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    entry_type: int = Field(sa_column=Column(INTEGER, nullable=False))
    event_identifier: str = Field(sa_column=Column(TEXT, nullable=False))
    sequence_index: int = Field(sa_column=Column(INTEGER, nullable=False))
    timestamp: int = Field(sa_column=Column(INTEGER, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        ),
    )
    location_label: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        ),
    )
    amount: str = Field(sa_column=Column(TEXT, nullable=False))
    notes: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    type: str = Field(sa_column=Column(TEXT, nullable=False))
    subtype: str = Field(sa_column=Column(TEXT, nullable=False))
    extra_data: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    ignored: int = Field(sa_column=Column(INTEGER, nullable=False, server_default='0'))

    # Relationships
    location_obj: Optional['Location'] = Relationship()
    asset_obj: Optional['Asset'] = Relationship(back_populates='history_events')
    mappings: list['HistoryEventMapping'] = Relationship(back_populates='event')
    evm_event_info: Optional['EvmEventInfo'] = Relationship(back_populates='event')

    def __repr__(self) -> str:
        return f"<HistoryEvent(identifier={self.identifier}, event_identifier='{self.event_identifier}')>"


class HistoryEventMapping(Base, table=True):
    """Model for history_events_mappings table"""
    __tablename__ = 'history_events_mappings'

    parent_identifier: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('history_events.identifier', onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    value: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))

    # Relationships
    event: 'HistoryEvent' = Relationship(back_populates='mappings')

    def __repr__(self) -> str:
        return f"<HistoryEventMapping(parent_identifier={self.parent_identifier}, name='{self.name}', value={self.value})>"


class EvmEventInfo(Base, table=True):
    """Model for evm_events_info table"""
    __tablename__ = 'evm_events_info'

    identifier: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('history_events.identifier', onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    tx_hash: bytes = Field(sa_column=Column(BLOB, nullable=False))
    counterparty: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    product: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    address: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

    # Relationships
    event: 'HistoryEvent' = Relationship(back_populates='evm_event_info')

    def __repr__(self) -> str:
        return f'<EvmEventInfo(identifier={self.identifier}, tx_hash={self.tx_hash.hex()})>'


class SkippedExternalEvent(Base, table=True):
    """Model for skipped_external_events table"""
    __tablename__ = 'skipped_external_events'
    __table_args__ = (
        UniqueConstraint('data', 'location'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    data: str = Field(sa_column=Column(TEXT, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        ),
    )
    extra_data: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

    # Relationships
    location_obj: Optional['Location'] = Relationship()

    def __repr__(self) -> str:
        return f"<SkippedExternalEvent(identifier={self.identifier}, location='{self.location}')>"
