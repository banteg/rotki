"""SQLAlchemy models for transient database tables"""

from typing import Optional

from sqlalchemy import (
    INTEGER, TEXT, VARCHAR, Column, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import FValType, TimestampType


class PnlReport(Base):
    """Model for PnL reports table"""
    __tablename__ = 'pnl_reports'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    timestamp: Mapped[Optional[int]] = mapped_column(TimestampType)
    start_ts: Mapped[Optional[int]] = mapped_column(TimestampType)
    end_ts: Mapped[Optional[int]] = mapped_column(TimestampType)
    first_processed_timestamp: Mapped[Optional[int]] = mapped_column(TimestampType)
    last_processed_timestamp: Mapped[int] = mapped_column(TimestampType, nullable=False)
    processed_actions: Mapped[int] = mapped_column(INTEGER, nullable=False)
    total_actions: Mapped[int] = mapped_column(INTEGER, nullable=False)
    
    # Relationships
    totals: Mapped[list['PnlReportTotal']] = relationship(
        back_populates='report',
        cascade='all, delete-orphan',
    )
    settings: Mapped[list['PnlReportSetting']] = relationship(
        back_populates='report',
        cascade='all, delete-orphan',
    )
    events: Mapped[list['PnlEvent']] = relationship(
        back_populates='report',
        cascade='all, delete-orphan',
    )
    
    def __repr__(self) -> str:
        return f"<PnlReport(id={self.identifier}, start={self.start_ts}, end={self.end_ts})>"


class PnlReportTotal(Base):
    """Model for PnL report totals table"""
    __tablename__ = 'pnl_report_totals'
    
    report_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('pnl_reports.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    taxable_value: Mapped[str] = mapped_column(FValType, nullable=False)
    free_value: Mapped[str] = mapped_column(FValType, nullable=False)
    
    # Relationships
    report: Mapped['PnlReport'] = relationship(back_populates='totals')
    
    def __repr__(self) -> str:
        return f"<PnlReportTotal(report_id={self.report_id}, name='{self.name}')>"


class PnlReportSetting(Base):
    """Model for PnL report settings table"""
    __tablename__ = 'pnl_report_settings'
    
    report_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('pnl_reports.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    type: Mapped[str] = mapped_column(TEXT, nullable=False)
    value: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    # Relationships
    report: Mapped['PnlReport'] = relationship(back_populates='settings')
    
    def __repr__(self) -> str:
        return f"<PnlReportSetting(report_id={self.report_id}, name='{self.name}')>"


class PnlEvent(Base):
    """Model for PnL events table"""
    __tablename__ = 'pnl_events'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    report_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('pnl_reports.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,
    )
    timestamp: Mapped[int] = mapped_column(TimestampType, nullable=False)
    data: Mapped[str] = mapped_column(TEXT, nullable=False)
    pnl_taxable: Mapped[str] = mapped_column(FValType, nullable=False)
    pnl_free: Mapped[str] = mapped_column(FValType, nullable=False)
    asset: Mapped[Optional[str]] = mapped_column(TEXT)
    
    # Relationships
    report: Mapped['PnlReport'] = relationship(back_populates='events')
    
    def __repr__(self) -> str:
        return f"<PnlEvent(id={self.identifier}, report_id={self.report_id}, timestamp={self.timestamp})>"


class TransientSettings(Base):
    """Model for settings table in transient database"""
    __tablename__ = 'settings'
    
    name: Mapped[str] = mapped_column(VARCHAR(24), primary_key=True, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(TEXT)
    
    def __repr__(self) -> str:
        return f"<TransientSettings(name='{self.name}', value='{self.value}')>"