"""Core SQLModel models for rotkehlchen database"""

from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    CHAR, INTEGER, TEXT, VARCHAR, Column, ForeignKey, Table, Computed
)
from sqlmodel import Field, Relationship

from rotkehlchen.db.orm.base_sqlmodel import UserDBBase
from rotkehlchen.db.orm.types import FValType, TimestampType

if TYPE_CHECKING:
    from rotkehlchen.db.orm.enums_sqlmodel import BalanceCategory, Location
    from rotkehlchen.db.orm.user_db_models_sqlmodel import EvmAccountDetails, XpubMapping


# Association table for many-to-many relationship between tags and other entities
tag_mappings = Table(
    'tag_mappings',
    UserDBBase.metadata,
    Column('object_reference', TEXT, primary_key=True, nullable=False),
    Column('tag_name', TEXT, ForeignKey('tags.name'), primary_key=True, nullable=False),
)


class UserSettings(UserDBBase, table=True):
    """Model for settings table in user database"""
    __tablename__ = 'settings'

    name: str = Field(
        sa_column=Column(VARCHAR(24), primary_key=True)
    )
    value: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<UserSettings(name='{self.name}', value='{self.value}')>"


class Asset(UserDBBase, table=True):
    """Model for assets table"""
    __tablename__ = 'assets'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True))

    # Relationships
    timed_balances: List['TimedBalance'] = Relationship(
        back_populates='asset',
        cascade_delete=True,
    )
    manually_tracked_balances: List['ManuallyTrackedBalance'] = Relationship(
        back_populates='asset_ref',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Asset(identifier='{self.identifier}')>"


class Tag(UserDBBase, table=True):
    """Model for tags table"""
    __tablename__ = 'tags'

    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    background_color: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    foreground_color: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<Tag(name='{self.name}')>"


class UserCredentials(UserDBBase, table=True):
    """Model for user credentials table"""
    __tablename__ = 'user_credentials'

    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            primary_key=True,
            nullable=False,
            server_default='A',
        )
    )
    api_key: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    api_secret: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    passphrase: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    location_ref: Optional['Location'] = Relationship()
    mappings: List['UserCredentialMapping'] = Relationship(
        back_populates='credential',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<UserCredentials(name='{self.name}', location='{self.location}')>"


class UserCredentialMapping(UserDBBase, table=True):
    """Model for user credentials mappings table"""
    __tablename__ = 'user_credentials_mappings'
    __table_args__ = (
        {'extend_existing': True}
    )

    credential_name: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('user_credentials.name'),
            primary_key=True,
            nullable=False,
        )
    )
    credential_location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            primary_key=True,
            nullable=False,
            server_default='A',
        )
    )
    setting_name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    setting_value: str = Field(sa_column=Column(TEXT, nullable=False))

    # Relationships
    credential: Optional['UserCredentials'] = Relationship(back_populates='mappings')

    def __repr__(self) -> str:
        return f"<UserCredentialMapping(name='{self.credential_name}', setting='{self.setting_name}')>"


class BlockchainAccount(UserDBBase, table=True):
    """Model for blockchain accounts table"""
    __tablename__ = 'blockchain_accounts'

    blockchain: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    account: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    # Relationships
    xpub_mappings: List['XpubMapping'] = Relationship(
        back_populates='account',
        cascade_delete=True,
    )
    evm_account_details: List['EvmAccountDetails'] = Relationship(
        back_populates='account',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<BlockchainAccount(blockchain='{self.blockchain}', account='{self.account}')>"


class TimedBalance(UserDBBase, table=True):
    """Model for timed balances table"""
    __tablename__ = 'timed_balances'

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
    amount: Optional[str] = Field(sa_column=Column(FValType))
    usd_value: Optional[str] = Field(sa_column=Column(FValType))

    # Relationships
    category_ref: Optional['BalanceCategory'] = Relationship()
    asset: Optional['Asset'] = Relationship(back_populates='timed_balances')

    def __repr__(self) -> str:
        return f"<TimedBalance(timestamp={self.timestamp}, currency='{self.currency}', amount={self.amount})>"


class TimedLocationData(UserDBBase, table=True):
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
    usd_value: Optional[str] = Field(sa_column=Column(FValType))

    # Relationships
    location_ref: Optional['Location'] = Relationship()

    def __repr__(self) -> str:
        return f"<TimedLocationData(timestamp={self.timestamp}, location='{self.location}', usd_value={self.usd_value})>"


class ManuallyTrackedBalance(UserDBBase, table=True):
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
    amount: Optional[str] = Field(sa_column=Column(FValType))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        )
    )
    category: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('balance_category.category'),
            nullable=False,
            server_default='A',
        )
    )

    # Relationships
    asset_ref: Optional['Asset'] = Relationship(back_populates='manually_tracked_balances')
    location_ref: Optional['Location'] = Relationship()
    category_ref: Optional['BalanceCategory'] = Relationship()

    def __repr__(self) -> str:
        return f"<ManuallyTrackedBalance(id={self.id}, asset='{self.asset}', label='{self.label}')>"


class IgnoredAction(UserDBBase, table=True):
    """Model for ignored actions table"""
    __tablename__ = 'ignored_actions'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True))

    def __repr__(self) -> str:
        return f"<IgnoredAction(identifier='{self.identifier}')>"