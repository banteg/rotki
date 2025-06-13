"""ETH staking models for user database"""

from typing import Optional

from sqlalchemy import INTEGER, TEXT, CheckConstraint, Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.user.base import Base


class Eth2Validator(Base, table=True):
    """Model for eth2_validators table"""
    __tablename__ = 'eth2_validators'
    __table_args__ = (
        CheckConstraint('validator_type IN (0, 1, 2)'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    validator_index: int | None = Field(
        default=None,
        sa_column=Column(INTEGER, unique=True, nullable=True),
    )
    public_key: str = Field(sa_column=Column(TEXT, unique=True, nullable=False))
    ownership_proportion: str = Field(sa_column=Column(TEXT, nullable=False))
    withdrawal_address: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    validator_type: int = Field(sa_column=Column(INTEGER, nullable=False))
    activation_timestamp: int | None = Field(default=None, sa_column=Column(INTEGER, nullable=True))
    withdrawable_timestamp: int | None = Field(default=None, sa_column=Column(INTEGER, nullable=True))
    exited_timestamp: int | None = Field(default=None, sa_column=Column(INTEGER, nullable=True))

    # Relationships
    daily_staking_details: list['Eth2DailyStakingDetails'] = Relationship(back_populates='validator')

    def __repr__(self) -> str:
        return f'<Eth2Validator(identifier={self.identifier}, validator_index={self.validator_index})>'


class Eth2DailyStakingDetails(Base, table=True):
    """Model for eth2_daily_staking_details table"""
    __tablename__ = 'eth2_daily_staking_details'

    validator_index: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('eth2_validators.validator_index', onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    timestamp: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    pnl: str = Field(sa_column=Column(TEXT, nullable=False))

    # Relationships
    validator: 'Eth2Validator' = Relationship(back_populates='daily_staking_details')

    def __repr__(self) -> str:
        return f'<Eth2DailyStakingDetails(validator_index={self.validator_index}, timestamp={self.timestamp})>'


class EthStakingEventInfo(Base, table=True):
    """Model for eth_staking_events_info table"""
    __tablename__ = 'eth_staking_events_info'

    identifier: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('history_events.identifier', onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    validator_index: int = Field(sa_column=Column(INTEGER, nullable=False))
    is_exit_or_blocknumber: int = Field(sa_column=Column(INTEGER, nullable=False))

    # Relationships
    history_event: Optional['HistoryEvent'] = Relationship()

    def __repr__(self) -> str:
        return f'<EthStakingEventInfo(identifier={self.identifier}, validator_index={self.validator_index})>'


class EthValidatorsDataCache(Base, table=True):
    """Model for eth_validators_data_cache table"""
    __tablename__ = 'eth_validators_data_cache'
    __table_args__ = (
        UniqueConstraint('validator_index', 'timestamp'),
    )

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    validator_index: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('eth2_validators.validator_index', onupdate='CASCADE', ondelete='CASCADE'),
            nullable=False,
        ),
    )
    timestamp: int = Field(sa_column=Column(INTEGER, nullable=False))
    balance: str = Field(sa_column=Column(TEXT, nullable=False))
    withdrawals_pnl: str = Field(sa_column=Column(TEXT, nullable=False))
    exit_pnl: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f'<EthValidatorsDataCache(id={self.id}, validator_index={self.validator_index})>'
