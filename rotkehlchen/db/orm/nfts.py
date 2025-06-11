"""SQLAlchemy models for NFT related tables"""

from typing import Optional

from sqlalchemy import (
    CHAR, INTEGER, REAL, TEXT, Column, ForeignKey, UniqueConstraint,
    CheckConstraint, text
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import BooleanType, FValType


class NFT(Base):
    """Model for NFTs table"""
    __tablename__ = 'nfts'
    
    identifier: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    last_price: Mapped[str] = mapped_column(FValType, nullable=False)
    last_price_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        nullable=False,
    )
    manual_price: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    owner_address: Mapped[Optional[str]] = mapped_column(TEXT)
    blockchain: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
        server_default=text("'ETH'"),
    )
    is_lp: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(TEXT)
    collection_name: Mapped[Optional[str]] = mapped_column(TEXT)
    usd_price: Mapped[float] = mapped_column(REAL, nullable=False, default=0)
    
    # Relationships
    asset: Mapped['Asset'] = relationship(foreign_keys=[identifier])
    price_asset: Mapped['Asset'] = relationship(foreign_keys=[last_price_asset])
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['blockchain', 'owner_address'],
            ['blockchain_accounts.blockchain', 'blockchain_accounts.account'],
            ondelete='CASCADE',
        ),
        CheckConstraint('manual_price IN (0, 1)'),
        CheckConstraint('is_lp IN (0, 1)'),
        # Virtual column for blockchain
        {'info': {'generated': True}},
    )
    
    def __repr__(self) -> str:
        return f"<NFT(identifier='{self.identifier}', name='{self.name}')>"


# Import to avoid circular dependency
from sqlalchemy import ForeignKeyConstraint