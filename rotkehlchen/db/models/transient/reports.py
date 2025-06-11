"""Report-related models for transient database using SQLModel"""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import INTEGER, TEXT, Column, ForeignKey
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.types import FValType, TimestampType
from rotkehlchen.db.models.transient.base import Base

if TYPE_CHECKING:
    pass


class PnlReport(Base, table=True):
    """Model for PnL reports table"""
    __tablename__ = 'pnl_reports'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    timestamp: Optional[int] = Field(default=None, sa_column=Column(TimestampType))
    start_ts: Optional[int] = Field(default=None, sa_column=Column(TimestampType))
    end_ts: Optional[int] = Field(default=None, sa_column=Column(TimestampType))
    first_processed_timestamp: Optional[int] = Field(default=None, sa_column=Column(TimestampType))
    last_processed_timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    processed_actions: int = Field(sa_column=Column(INTEGER, nullable=False))
    total_actions: int = Field(sa_column=Column(INTEGER, nullable=False))

    # Relationships
    totals: List['PnlReportTotal'] = Relationship(
        back_populates='report',
        cascade_delete=True,
    )
    settings: List['PnlReportSetting'] = Relationship(
        back_populates='report',
        cascade_delete=True,
    )
    events: List['PnlEvent'] = Relationship(
        back_populates='report',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f'<PnlReport(id={self.identifier}, start={self.start_ts}, end={self.end_ts})>'


class PnlReportTotal(Base, table=True):
    """Model for PnL report totals table"""
    __tablename__ = 'pnl_report_totals'

    report_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('pnl_reports.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    taxable_value: str = Field(sa_column=Column(FValType, nullable=False))
    free_value: str = Field(sa_column=Column(FValType, nullable=False))

    # Relationships
    report: Optional['PnlReport'] = Relationship(back_populates='totals')

    def __repr__(self) -> str:
        return f"<PnlReportTotal(report_id={self.report_id}, name='{self.name}')>"


class PnlReportSetting(Base, table=True):
    """Model for PnL report settings table"""
    __tablename__ = 'pnl_report_settings'

    report_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('pnl_reports.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    type: str = Field(sa_column=Column(TEXT, nullable=False))
    value: str = Field(sa_column=Column(TEXT, nullable=False))

    # Relationships
    report: Optional['PnlReport'] = Relationship(back_populates='settings')

    def __repr__(self) -> str:
        return f"<PnlReportSetting(report_id={self.report_id}, name='{self.name}')>"


class PnlEvent(Base, table=True):
    """Model for PnL events table"""
    __tablename__ = 'pnl_events'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    report_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('pnl_reports.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            nullable=False,
        )
    )
    timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    data: str = Field(sa_column=Column(TEXT, nullable=False))
    pnl_taxable: str = Field(sa_column=Column(FValType, nullable=False))
    pnl_free: str = Field(sa_column=Column(FValType, nullable=False))
    asset: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    report: Optional['PnlReport'] = Relationship(back_populates='events')

    def __repr__(self) -> str:
        return f"<PnlEvent(id={self.identifier}, report_id={self.report_id}, asset='{self.asset}')>"