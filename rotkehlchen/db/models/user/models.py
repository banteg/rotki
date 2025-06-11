"""Core user database models using SQLModel"""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    CHAR, INTEGER, REAL, TEXT, VARCHAR, CheckConstraint, Column, ForeignKey,
    ForeignKeyConstraint, Index, UniqueConstraint,
)
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.types import BooleanType, FValType, TimestampType
from rotkehlchen.db.models.user.base import Base

if TYPE_CHECKING:
    from rotkehlchen.db.models.user.accounts import BlockchainAccount
    from rotkehlchen.db.models.user.credentials import UserCredentialMapping
    from rotkehlchen.db.models.user.enums import BalanceCategory, Location
    from rotkehlchen.db.models.user.nfts import NFT


class Asset(Base, table=True):
    """Model for assets table"""
    __tablename__ = 'assets'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    # Relationships
    timed_balances: List['TimedBalance'] = Relationship(
        back_populates='currency_obj',
        cascade_delete=True,
    )
    location_data: List['TimedLocationData'] = Relationship(
        back_populates='currency_obj',
        cascade_delete=True,
    )
    manually_tracked_balances: List['ManuallyTrackedBalance'] = Relationship(
        back_populates='asset_obj',
        cascade_delete=True,
    )
    nfts: List['NFT'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[NFT.identifier]'},
        cascade_delete=True,
    )
    nft_price_assets: List['NFT'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[NFT.last_price_asset]'},
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Asset(identifier='{self.identifier}')>"


class Tag(Base, table=True):
    """Model for tags table"""
    __tablename__ = 'tags'

    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    background_color: str = Field(sa_column=Column(TEXT, nullable=False))
    foreground_color: str = Field(sa_column=Column(TEXT, nullable=False))

    # Relationships
    accounts: List['BlockchainAccount'] = Relationship(
        back_populates='tag_obj',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Tag(name='{self.name}')>"


class UserSettings(Base, table=True):
    """Model for user settings table"""
    __tablename__ = 'user_settings'

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<UserSettings(name='{self.name}', value='{self.value}')>"


class TimedBalance(Base, table=True):
    """Model for timed balances table"""
    __tablename__ = 'timed_balances'
    __table_args__ = (
        ForeignKeyConstraint(
            ['category', 'time', 'currency', 'amount', 'usd_value'],
            [
                'manually_tracked_balances.category',
                'manually_tracked_balances.time',
                'manually_tracked_balances.currency',
                'manually_tracked_balances.amount',
                'manually_tracked_balances.usd_value',
            ],
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
    )

    category: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('balance_category.category'),
            primary_key=True,
            nullable=False,
            server_default='A',
        )
    )
    timestamp: int = Field(sa_column=Column(TimestampType, primary_key=True, nullable=False))
    currency: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    amount: str = Field(sa_column=Column(FValType, primary_key=True, nullable=False))
    usd_value: str = Field(sa_column=Column(FValType, primary_key=True, nullable=False))

    # Relationships
    category_obj: Optional['BalanceCategory'] = Relationship()
    currency_obj: Optional['Asset'] = Relationship(back_populates='timed_balances')

    def __repr__(self) -> str:
        return f"<TimedBalance(category='{self.category}', time={self.timestamp}, currency='{self.currency}')>"


class TimedLocationData(Base, table=True):
    """Model for timed location data table"""
    __tablename__ = 'timed_location_data'

    timestamp: int = Field(sa_column=Column(TimestampType, primary_key=True, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            primary_key=True,
            nullable=False,
            server_default='A',
        )
    )
    usd_value: str = Field(sa_column=Column(FValType, primary_key=True, nullable=False))

    # Relationships
    location_obj: Optional['Location'] = Relationship()

    def __repr__(self) -> str:
        return f"<TimedLocationData(time={self.timestamp}, location='{self.location}', usd_value={self.usd_value})>"


class ManuallyTrackedBalance(Base, table=True):
    """Model for manually tracked balances table"""
    __tablename__ = 'manually_tracked_balances'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    label: str = Field(sa_column=Column(TEXT, nullable=False))
    amount: str = Field(sa_column=Column(FValType, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        )
    )
    tags: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    balance_type: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('balance_category.category'),
            nullable=False,
            server_default='A',
        )
    )

    # Relationships
    asset_obj: Optional['Asset'] = Relationship(back_populates='manually_tracked_balances')
    location_obj: Optional['Location'] = Relationship()
    balance_type_obj: Optional['BalanceCategory'] = Relationship()

    def __repr__(self) -> str:
        return f"<ManuallyTrackedBalance(id={self.id}, asset='{self.asset}', label='{self.label}')>"


class IgnoredAction(Base, table=True):
    """Model for ignored actions table"""
    __tablename__ = 'ignored_actions'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    def __repr__(self) -> str:
        return f"<IgnoredAction(identifier='{self.identifier}')>"