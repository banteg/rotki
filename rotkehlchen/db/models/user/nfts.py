"""NFT-related models for user database using SQLModel"""

from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    REAL, TEXT, CheckConstraint, Computed, ForeignKey, ForeignKeyConstraint, Column
)
from sqlmodel import Field, Relationship

from rotkehlchen.db.orm.types import BooleanType, FValType
from rotkehlchen.db.orm.userdb.base import Base

if TYPE_CHECKING:
    from rotkehlchen.db.orm.userdb.models import Asset


class NFT(Base, table=True):
    """Model for NFTs table"""
    __tablename__ = 'nfts'
    __table_args__ = (
        ForeignKeyConstraint(
            ['blockchain', 'owner_address'],
            ['blockchain_accounts.blockchain', 'blockchain_accounts.account'],
            ondelete='CASCADE',
        ),
        CheckConstraint('manual_price IN (0, 1)'),
        CheckConstraint('is_lp IN (0, 1)'),
    )

    identifier: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    name: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    last_price: str = Field(sa_column=Column(FValType, nullable=False))
    last_price_asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    manual_price: bool = Field(sa_column=Column(BooleanType, nullable=False))
    owner_address: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    blockchain: str = Field(
        sa_column=Column(
            TEXT,
            Computed("'ETH'", persisted=False),  # GENERATED ALWAYS AS ('ETH') VIRTUAL
            nullable=False,
        )
    )
    is_lp: bool = Field(sa_column=Column(BooleanType, nullable=False))
    image_url: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    collection_name: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    usd_price: float = Field(sa_column=Column(REAL, nullable=False, server_default='0'))

    # Relationships
    asset: Optional['Asset'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[NFT.identifier]'},
        back_populates='nfts',
    )
    price_asset: Optional['Asset'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[NFT.last_price_asset]'},
        back_populates='nft_price_assets',
    )

    def __repr__(self) -> str:
        return f"<NFT(identifier='{self.identifier}', name='{self.name}')>"