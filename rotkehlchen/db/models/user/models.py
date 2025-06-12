"""Core user database models using SQLModel"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CHAR,
    INTEGER,
    TEXT,
    VARCHAR,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
)
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.types import FValType, TimestampType
from rotkehlchen.db.models.user.base import Base

if TYPE_CHECKING:

    from rotkehlchen.db.models.user.accounts import BlockchainAccount
    from rotkehlchen.db.models.user.enums import BalanceCategory, Location
    from rotkehlchen.db.models.user.nfts import NFT


class Asset(Base, table=True):
    """Model for assets table"""
    __tablename__ = 'assets'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    # Relationships
    timed_balances: list['TimedBalance'] = Relationship(
        back_populates='currency_obj',
        cascade_delete=True,
    )
    location_data: list['TimedLocationData'] = Relationship(
        back_populates='currency_obj',
        cascade_delete=True,
    )
    manually_tracked_balances: list['ManuallyTrackedBalance'] = Relationship(
        back_populates='asset_obj',
        cascade_delete=True,
    )
    nfts: list['NFT'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[NFT.identifier]'},
        cascade_delete=True,
    )
    nft_price_assets: list['NFT'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[NFT.last_price_asset]'},
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Asset(identifier='{self.identifier}')>"


class Tag(Base, table=True):
    """Model for tags table"""
    __tablename__ = 'tags'

    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(TEXT))
    background_color: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    foreground_color: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

    def __repr__(self) -> str:
        return f"<Tag(name='{self.name}')>"


class TagMapping(Base, table=True):
    """Model for tag_mappings table"""
    __tablename__ = 'tag_mappings'

    object_reference: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    tag_name: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('tags.name'),
            primary_key=True,
            nullable=False,
        ),
    )

    # Relationships
    tag: Optional['Tag'] = Relationship()

    def __repr__(self) -> str:
        return f"<TagMapping(object_reference='{self.object_reference}', tag_name='{self.tag_name}')>"


class Settings(Base, table=True):
    """Model for user settings table"""
    __tablename__ = 'settings'

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    value: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

    def __repr__(self) -> str:
        return f"<Settings(name='{self.name}', value='{self.value}')>"


class TimedBalance(Base, table=True):
    """Model for timed balances table"""
    __tablename__ = 'timed_balances'

    timestamp: int = Field(sa_column=Column(TimestampType, primary_key=True, nullable=False))
    currency: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    category: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('balance_category.category'),
            primary_key=True,
            nullable=False,
            server_default='A',
        ),
    )
    amount: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    usd_value: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

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
        ),
    )
    usd_value: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

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
        ),
    )
    label: str = Field(sa_column=Column(TEXT, nullable=False))
    amount: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        ),
    )
    category: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('balance_category.category'),
            nullable=False,
            server_default='A',
        ),
    )

    # Relationships
    asset_obj: Optional['Asset'] = Relationship(back_populates='manually_tracked_balances')
    location_obj: Optional['Location'] = Relationship()
    category_obj: Optional['BalanceCategory'] = Relationship()

    def __repr__(self) -> str:
        return f"<ManuallyTrackedBalance(id={self.id}, asset='{self.asset}', label='{self.label}')>"


class IgnoredAction(Base, table=True):
    """Model for ignored actions table"""
    __tablename__ = 'ignored_actions'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    def __repr__(self) -> str:
        return f"<IgnoredAction(identifier='{self.identifier}')>"
