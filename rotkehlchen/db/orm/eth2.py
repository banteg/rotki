"""SQLAlchemy models for ETH2 staking related tables"""


from sqlalchemy import (
    INTEGER,
    TEXT,
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import FValType, TimestampType


class Eth2Validator(Base):
    """Model for ETH2 validators table"""
    __tablename__ = 'eth2_validators'

    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    validator_index: Mapped[int | None] = mapped_column(INTEGER, unique=True)
    public_key: Mapped[str] = mapped_column(TEXT, unique=True, nullable=False)
    ownership_proportion: Mapped[str] = mapped_column(FValType, nullable=False)
    withdrawal_address: Mapped[str | None] = mapped_column(TEXT)
    validator_type: Mapped[int] = mapped_column(INTEGER, nullable=False)
    activation_timestamp: Mapped[int | None] = mapped_column(TimestampType)
    withdrawable_timestamp: Mapped[int | None] = mapped_column(TimestampType)
    exited_timestamp: Mapped[int | None] = mapped_column(TimestampType)

    # Relationships
    data_cache: Mapped[list['EthValidatorsDataCache']] = relationship(
        back_populates='validator',
        cascade='all, delete-orphan',
    )
    daily_staking_details: Mapped[list['Eth2DailyStakingDetails']] = relationship(
        back_populates='validator',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        CheckConstraint('validator_type IN (0, 1, 2)'),
    )

    def __repr__(self) -> str:
        return f'<Eth2Validator(id={self.identifier}, index={self.validator_index})>'


class EthValidatorsDataCache(Base):
    """Model for ETH validators data cache table"""
    __tablename__ = 'eth_validators_data_cache'

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    validator_index: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('eth2_validators.validator_index', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,
    )
    timestamp: Mapped[int] = mapped_column(INTEGER, nullable=False)  # milliseconds
    balance: Mapped[str] = mapped_column(FValType, nullable=False)
    withdrawals_pnl: Mapped[str] = mapped_column(FValType, nullable=False)
    exit_pnl: Mapped[str] = mapped_column(FValType, nullable=False)

    # Relationships
    validator: Mapped['Eth2Validator'] = relationship(back_populates='data_cache')

    __table_args__ = (
        UniqueConstraint('validator_index', 'timestamp'),
    )

    def __repr__(self) -> str:
        return f'<EthValidatorsDataCache(id={self.id}, validator={self.validator_index})>'


class Eth2DailyStakingDetails(Base):
    """Model for ETH2 daily staking details table"""
    __tablename__ = 'eth2_daily_staking_details'

    validator_index: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('eth2_validators.validator_index', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    timestamp: Mapped[int] = mapped_column(TimestampType, primary_key=True, nullable=False)
    pnl: Mapped[str] = mapped_column(FValType, nullable=False)

    # Relationships
    validator: Mapped['Eth2Validator'] = relationship(back_populates='daily_staking_details')

    def __repr__(self) -> str:
        return f'<Eth2DailyStakingDetails(validator={self.validator_index}, timestamp={self.timestamp})>'
