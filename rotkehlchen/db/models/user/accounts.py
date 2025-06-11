"""Account-related models for user database using SQLModel"""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    CHAR, INTEGER, TEXT, VARCHAR, Column, ForeignKey, ForeignKeyConstraint, UniqueConstraint,
)
from sqlmodel import Field, Relationship

from rotkehlchen.db.orm.types import TimestampType
from rotkehlchen.db.orm.userdb.base import Base

if TYPE_CHECKING:
    from rotkehlchen.db.orm.userdb.models import Tag
    from rotkehlchen.db.orm.userdb.xpubs import XpubMapping


class UserCredentials(Base, table=True):
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


class UserCredentialMapping(Base, table=True):
    """Model for user credential mappings table"""
    __tablename__ = 'user_credentials_mappings'
    __table_args__ = (
        ForeignKeyConstraint(
            ['credential_name', 'credential_location'],
            ['user_credentials.name', 'user_credentials.location'],
            ondelete='CASCADE',
            onupdate='CASCADE',
        ),
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


class BlockchainAccount(Base, table=True):
    """Model for blockchain accounts table"""
    __tablename__ = 'blockchain_accounts'

    blockchain: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    account: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    label: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    tag: Optional[str] = Field(
        default=None,
        sa_column=Column(TEXT, ForeignKey('tags.name', onupdate='CASCADE'))
    )

    # Relationships
    tag_obj: Optional['Tag'] = Relationship(back_populates='accounts')
    xpub_mappings: List['XpubMapping'] = Relationship(
        cascade_delete=True,
    )
    evm_details: List['EvmAccountDetails'] = Relationship(
        back_populates='account_obj',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<BlockchainAccount(blockchain='{self.blockchain}', account='{self.account}')>"


class EvmAccountDetails(Base, table=True):
    """Model for EVM account details table"""
    __tablename__ = 'evm_accounts_details'

    account: str = Field(
        sa_column=Column(
            VARCHAR(42),
            ForeignKey('blockchain_accounts.account'),
            primary_key=True,
            nullable=False,
        )
    )
    chain_id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    last_queried_timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))

    # Relationships
    account_obj: Optional['BlockchainAccount'] = Relationship(back_populates='evm_details')

    def __repr__(self) -> str:
        return f"<EvmAccountDetails(account='{self.account}', chain_id={self.chain_id})"