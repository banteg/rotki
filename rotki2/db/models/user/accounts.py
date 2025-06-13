"""Account-related models for user database using SQLModel"""

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

from rotki2.db.models.user.base import Base

if TYPE_CHECKING:
    from rotki2.db.models.user.xpubs import XpubMapping


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
        ),
    )
    api_key: str | None = Field(default=None, sa_column=Column(TEXT))
    api_secret: str | None = Field(default=None, sa_column=Column(TEXT))
    passphrase: str | None = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    location_ref: Optional['Location'] = Relationship()
    mappings: list['UserCredentialMapping'] = Relationship(
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
        ),
    )
    credential_location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            primary_key=True,
            nullable=False,
            server_default='A',
        ),
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

    # Relationships
    xpub_mappings: list['XpubMapping'] = Relationship(
        cascade_delete=True,
    )
    evm_details: list['EvmAccountDetails'] = Relationship(
        back_populates='account_obj',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<BlockchainAccount(blockchain='{self.blockchain}', account='{self.account}')>"


class EvmAccountDetails(Base, table=True):
    """Model for EVM account details table"""
    __tablename__ = 'evm_accounts_details'

    account: str = Field(sa_column=Column(VARCHAR(42), primary_key=True, nullable=False))
    chain_id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    key: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    def __repr__(self) -> str:
        return f"<EvmAccountDetails(account='{self.account}', chain_id={self.chain_id})"
