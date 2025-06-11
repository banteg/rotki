"""Core SQLAlchemy models for rotkehlchen database"""

from typing import Optional

from sqlalchemy import (
    CHAR, INTEGER, TEXT, VARCHAR, Column, ForeignKey, UniqueConstraint,
    CheckConstraint, Index, Table
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import (
    BooleanType, CharEnumType, FValType, HexBytesType, TimestampType
)


# Association table for many-to-many relationship between tags and other entities
tag_mappings = Table(
    'tag_mappings',
    Base.metadata,
    Column('object_reference', TEXT, primary_key=True),
    Column('tag_name', TEXT, ForeignKey('tags.name'), primary_key=True),
)


class Settings(Base):
    """Model for settings table"""
    __tablename__ = 'settings'
    
    name: Mapped[str] = mapped_column(VARCHAR(24), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(TEXT)
    
    def __repr__(self) -> str:
        return f"<Settings(name='{self.name}', value='{self.value}')>"


class Asset(Base):
    """Model for assets table"""
    __tablename__ = 'assets'
    
    identifier: Mapped[str] = mapped_column(TEXT, primary_key=True)
    
    # Relationships
    timed_balances: Mapped[list['TimedBalance']] = relationship(
        back_populates='asset',
        cascade='all, delete-orphan',
    )
    manually_tracked_balances: Mapped[list['ManuallyTrackedBalance']] = relationship(
        back_populates='asset',
        cascade='all, delete-orphan',
    )
    
    def __repr__(self) -> str:
        return f"<Asset(identifier='{self.identifier}')>"


class Tag(Base):
    """Model for tags table"""
    __tablename__ = 'tags'
    
    name: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    background_color: Mapped[Optional[str]] = mapped_column(TEXT)
    foreground_color: Mapped[Optional[str]] = mapped_column(TEXT)
    
    def __repr__(self) -> str:
        return f"<Tag(name='{self.name}')>"


class UserCredentials(Base):
    """Model for user credentials table"""
    __tablename__ = 'user_credentials'
    
    name: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    location: Mapped[str] = mapped_column(
        CHAR(1), 
        ForeignKey('location.location'),
        primary_key=True,
        nullable=False,
        default='A',
    )
    api_key: Mapped[Optional[str]] = mapped_column(TEXT)
    api_secret: Mapped[Optional[str]] = mapped_column(TEXT)
    passphrase: Mapped[Optional[str]] = mapped_column(TEXT)
    
    # Relationships
    location_ref: Mapped['Location'] = relationship()
    mappings: Mapped[list['UserCredentialMapping']] = relationship(
        back_populates='credential',
        cascade='all, delete-orphan',
    )
    
    def __repr__(self) -> str:
        return f"<UserCredentials(name='{self.name}', location='{self.location}')>"


class UserCredentialMapping(Base):
    """Model for user credentials mappings table"""
    __tablename__ = 'user_credentials_mappings'
    
    credential_name: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('user_credentials.name'),
        primary_key=True,
        nullable=False,
    )
    credential_location: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('user_credentials.location'),
        primary_key=True,
        nullable=False,
        default='A',
    )
    setting_name: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    # Relationships
    credential: Mapped['UserCredentials'] = relationship(back_populates='mappings')
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['credential_name', 'credential_location'],
            ['user_credentials.name', 'user_credentials.location'],
            ondelete='CASCADE',
            onupdate='CASCADE',
        ),
    )
    
    def __repr__(self) -> str:
        return f"<UserCredentialMapping(name='{self.credential_name}', setting='{self.setting_name}')>"


class BlockchainAccount(Base):
    """Model for blockchain accounts table"""
    __tablename__ = 'blockchain_accounts'
    
    blockchain: Mapped[str] = mapped_column(VARCHAR(24), primary_key=True, nullable=False)
    account: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    
    # Relationships
    xpub_mappings: Mapped[list['XpubMapping']] = relationship(
        back_populates='account',
        cascade='all, delete-orphan',
    )
    evm_account_details: Mapped[list['EvmAccountDetails']] = relationship(
        back_populates='account',
        cascade='all, delete-orphan',
    )
    
    def __repr__(self) -> str:
        return f"<BlockchainAccount(blockchain='{self.blockchain}', account='{self.account}')>"


class TimedBalance(Base):
    """Model for timed balances table"""
    __tablename__ = 'timed_balances'
    
    category: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('balance_category.category'),
        primary_key=True,
        nullable=False,
        default='A',
    )
    timestamp: Mapped[int] = mapped_column(TimestampType, primary_key=True)
    currency: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        primary_key=True,
    )
    amount: Mapped[str] = mapped_column(FValType)
    usd_value: Mapped[str] = mapped_column(FValType)
    
    # Relationships
    category_ref: Mapped['BalanceCategory'] = relationship()
    asset: Mapped['Asset'] = relationship(back_populates='timed_balances')
    
    def __repr__(self) -> str:
        return f"<TimedBalance(timestamp={self.timestamp}, currency='{self.currency}', amount={self.amount})>"


class ManuallyTrackedBalance(Base):
    """Model for manually tracked balances table"""
    __tablename__ = 'manually_tracked_balances'
    
    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(TEXT, nullable=False)
    amount: Mapped[Optional[str]] = mapped_column(FValType)
    location: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('location.location'),
        nullable=False,
        default='A',
    )
    category: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('balance_category.category'),
        nullable=False,
        default='A',
    )
    
    # Relationships
    asset_ref: Mapped['Asset'] = relationship(back_populates='manually_tracked_balances')
    location_ref: Mapped['Location'] = relationship()
    category_ref: Mapped['BalanceCategory'] = relationship()
    
    def __repr__(self) -> str:
        return f"<ManuallyTrackedBalance(id={self.id}, asset='{self.asset}', label='{self.label}')>"


# Import to avoid circular dependency
from sqlalchemy import ForeignKeyConstraint