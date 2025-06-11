"""Xpub-related models for user database using SQLModel"""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import INTEGER, TEXT, VARCHAR, Column, ForeignKey
from sqlmodel import Field, Relationship

from rotkehlchen.db.orm.userdb.base import Base

if TYPE_CHECKING:
    from rotkehlchen.db.orm.userdb.accounts import BlockchainAccount


class Xpub(Base, table=True):
    """Model for xpubs table"""
    __tablename__ = 'xpubs'

    xpub: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    derivation_path: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    label: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    mappings: List['XpubMapping'] = Relationship(
        back_populates='xpub_obj',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Xpub(xpub='{self.xpub}', label='{self.label}')>"


class XpubMapping(Base, table=True):
    """Model for xpub mappings table"""
    __tablename__ = 'xpub_mappings'

    xpub: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('xpubs.xpub', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    derivation_path: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    account_index: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    derived_index: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    blockchain: str = Field(
        sa_column=Column(
            VARCHAR(24),
            ForeignKey('blockchain_accounts.blockchain'),
            nullable=False,
        )
    )

    # Relationships
    xpub_obj: Optional['Xpub'] = Relationship(back_populates='mappings')
    account: Optional['BlockchainAccount'] = Relationship(back_populates='xpub_mappings')

    def __repr__(self) -> str:
        return f"<XpubMapping(xpub='{self.xpub}', address='{self.address}')>"