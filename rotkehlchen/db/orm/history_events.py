"""SQLAlchemy models for history events tables"""

from typing import Optional

from sqlalchemy import (
    BLOB, CHAR, INTEGER, TEXT, Column, ForeignKey, UniqueConstraint,
    CheckConstraint, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import (
    BooleanType, FValType, HexBytesType, TimestampType
)


class HistoryEvent(Base):
    """Model for history events table"""
    __tablename__ = 'history_events'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    entry_type: Mapped[int] = mapped_column(INTEGER, nullable=False)
    event_identifier: Mapped[str] = mapped_column(TEXT, nullable=False)
    sequence_index: Mapped[int] = mapped_column(INTEGER, nullable=False)
    timestamp: Mapped[int] = mapped_column(TimestampType, nullable=False)
    location: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('location.location'),
        nullable=False,
        default='A',
    )
    location_label: Mapped[Optional[str]] = mapped_column(TEXT)
    asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        nullable=False,
    )
    amount: Mapped[str] = mapped_column(FValType, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(TEXT)
    type: Mapped[str] = mapped_column(TEXT, nullable=False)
    subtype: Mapped[str] = mapped_column(TEXT, nullable=False)
    extra_data: Mapped[Optional[str]] = mapped_column(TEXT)
    ignored: Mapped[bool] = mapped_column(BooleanType, nullable=False, default=False)
    
    # Relationships
    location_ref: Mapped['Location'] = relationship()
    asset_ref: Mapped['Asset'] = relationship()
    evm_info: Mapped[Optional['EvmEventInfo']] = relationship(
        back_populates='event',
        cascade='all, delete-orphan',
        uselist=False,
    )
    staking_info: Mapped[Optional['EthStakingEventInfo']] = relationship(
        back_populates='event',
        cascade='all, delete-orphan',
        uselist=False,
    )
    mappings: Mapped[list['HistoryEventMapping']] = relationship(
        back_populates='event',
        cascade='all, delete-orphan',
    )
    
    __table_args__ = (
        UniqueConstraint('event_identifier', 'sequence_index'),
        # Performance indexes
        Index('idx_history_events_entry_type', 'entry_type'),
        Index('idx_history_events_timestamp', 'timestamp'),
        Index('idx_history_events_location', 'location'),
        Index('idx_history_events_location_label', 'location_label'),
        Index('idx_history_events_asset', 'asset'),
        Index('idx_history_events_type', 'type'),
        Index('idx_history_events_subtype', 'subtype'),
        Index('idx_history_events_ignored', 'ignored'),
    )
    
    def __repr__(self) -> str:
        return f"<HistoryEvent(id={self.identifier}, type='{self.type}', timestamp={self.timestamp})>"


class EvmEventInfo(Base):
    """Model for EVM-specific event information"""
    __tablename__ = 'evm_events_info'
    
    identifier: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('history_events.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
    )
    tx_hash: Mapped[bytes] = mapped_column(HexBytesType, nullable=False)
    counterparty: Mapped[Optional[str]] = mapped_column(TEXT)
    product: Mapped[Optional[str]] = mapped_column(TEXT)
    address: Mapped[Optional[str]] = mapped_column(TEXT)
    
    # Relationships
    event: Mapped['HistoryEvent'] = relationship(back_populates='evm_info')
    
    def __repr__(self) -> str:
        return f"<EvmEventInfo(id={self.identifier}, tx_hash='{self.tx_hash}')>"


class EthStakingEventInfo(Base):
    """Model for Ethereum staking event information"""
    __tablename__ = 'eth_staking_events_info'
    
    identifier: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('history_events.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
    )
    validator_index: Mapped[int] = mapped_column(INTEGER, nullable=False)
    is_exit_or_blocknumber: Mapped[int] = mapped_column(INTEGER, nullable=False)
    
    # Relationships
    event: Mapped['HistoryEvent'] = relationship(back_populates='staking_info')
    
    def __repr__(self) -> str:
        return f"<EthStakingEventInfo(id={self.identifier}, validator_index={self.validator_index})>"


class HistoryEventMapping(Base):
    """Model for history event mappings"""
    __tablename__ = 'history_events_mappings'
    
    parent_identifier: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('history_events.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    value: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    
    # Relationships
    event: Mapped['HistoryEvent'] = relationship(back_populates='mappings')
    
    def __repr__(self) -> str:
        return f"<HistoryEventMapping(parent={self.parent_identifier}, name='{self.name}', value={self.value})>"


class SkippedExternalEvent(Base):
    """Model for skipped external events"""
    __tablename__ = 'skipped_external_events'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    data: Mapped[str] = mapped_column(TEXT, nullable=False)
    location: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('location.location'),
        nullable=False,
        default='A',
    )
    extra_data: Mapped[Optional[str]] = mapped_column(TEXT)
    
    # Relationships
    location_ref: Mapped['Location'] = relationship()
    
    __table_args__ = (
        UniqueConstraint('data', 'location'),
    )
    
    def __repr__(self) -> str:
        return f"<SkippedExternalEvent(id={self.identifier}, location='{self.location}')>"