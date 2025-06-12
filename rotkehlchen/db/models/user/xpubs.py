"""Xpub-related models for user database using SQLModel"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import INTEGER, TEXT, VARCHAR, Column, ForeignKey, ForeignKeyConstraint
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.user.base import Base

if TYPE_CHECKING:
    from rotkehlchen.db.orm.userdb.accounts import BlockchainAccount


class Xpub(Base, table=True):
    """Model for xpubs table"""
    __tablename__ = 'xpubs'

    xpub: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    derivation_path: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    blockchain: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    label: str | None = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    mappings: list['XpubMapping'] = Relationship(
        back_populates='xpub_obj',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Xpub(xpub='{self.xpub}', label='{self.label}')>"


class XpubMapping(Base, table=True):
    """Model for xpub mappings table"""
    __tablename__ = 'xpub_mappings'
    __table_args__ = (
        ForeignKeyConstraint(
            ['blockchain', 'address'],
            ['blockchain_accounts.blockchain', 'blockchain_accounts.account'],
            ondelete='CASCADE',
        ),
        ForeignKeyConstraint(
            ['xpub', 'derivation_path', 'blockchain'],
            ['xpubs.xpub', 'xpubs.derivation_path', 'xpubs.blockchain'],
            ondelete='CASCADE',
        ),
    )

    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    xpub: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    derivation_path: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    account_index: int | None = Field(default=None, sa_column=Column(INTEGER, nullable=True))
    derived_index: int | None = Field(default=None, sa_column=Column(INTEGER, nullable=True))
    blockchain: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    # Relationships
    xpub_obj: Optional['Xpub'] = Relationship(back_populates='mappings')
    account: Optional['BlockchainAccount'] = Relationship(back_populates='xpub_mappings')

    def __repr__(self) -> str:
        return f"<XpubMapping(xpub='{self.xpub}', address='{self.address}')>"
