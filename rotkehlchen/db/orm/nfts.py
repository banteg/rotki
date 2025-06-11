"""SQLAlchemy models for NFT related tables"""

from typing import TYPE_CHECKING

from sqlalchemy import (
    REAL,
    TEXT,
    CheckConstraint,
    Computed,
    ForeignKey,
    ForeignKeyConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rotkehlchen.db.orm.base import UserDBBase as Base
from rotkehlchen.db.orm.types import BooleanType, FValType

if TYPE_CHECKING:
    from rotkehlchen.db.orm.models import Asset


class NFT(Base):
    """Model for NFTs table"""
    __tablename__ = 'nfts'

    identifier: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(TEXT)
    last_price: Mapped[str] = mapped_column(FValType, nullable=False)
    last_price_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        nullable=False,
    )
    manual_price: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    owner_address: Mapped[str | None] = mapped_column(TEXT)
    blockchain: Mapped[str] = mapped_column(
        TEXT,
        Computed("'ETH'", persisted=False),  # GENERATED ALWAYS AS ('ETH') VIRTUAL
        nullable=False,
    )
    is_lp: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    image_url: Mapped[str | None] = mapped_column(TEXT)
    collection_name: Mapped[str | None] = mapped_column(TEXT)
    usd_price: Mapped[float] = mapped_column(REAL, nullable=False, server_default='0')

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
    )

    def __repr__(self) -> str:
        return f"<NFT(identifier='{self.identifier}', name='{self.name}')>"


# Import to avoid circular dependency
