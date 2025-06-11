"""SQLAlchemy models for ZkSync Lite tables"""

from typing import Optional

from sqlalchemy import (
    BLOB, CHAR, INTEGER, TEXT, Column, ForeignKey, UniqueConstraint,
    CheckConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import (
    BooleanType, FValType, HexBytesType, TimestampType
)


class ZkSyncLiteTransaction(Base):
    """Model for ZkSync Lite transactions table"""
    __tablename__ = 'zksynclite_transactions'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    tx_hash: Mapped[bytes] = mapped_column(HexBytesType, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('zksynclite_tx_type.type'),
        nullable=False,
        default='A',
    )
    is_decoded: Mapped[bool] = mapped_column(BooleanType, nullable=False, default=False)
    timestamp: Mapped[int] = mapped_column(TimestampType, nullable=False)
    block_number: Mapped[int] = mapped_column(INTEGER, nullable=False)
    from_address: Mapped[str] = mapped_column(TEXT, nullable=False)
    to_address: Mapped[Optional[str]] = mapped_column(TEXT)
    asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        nullable=False,
    )
    amount: Mapped[str] = mapped_column(FValType, nullable=False)
    fee: Mapped[Optional[str]] = mapped_column(FValType)
    
    # Relationships
    type_ref: Mapped['ZkSyncLiteTxType'] = relationship()
    asset_ref: Mapped['Asset'] = relationship()
    swap: Mapped[Optional['ZkSyncLiteSwap']] = relationship(
        back_populates='transaction',
        cascade='all, delete-orphan',
        uselist=False,
    )
    
    __table_args__ = (
        CheckConstraint('is_decoded IN (0, 1)'),
    )
    
    def __repr__(self) -> str:
        return f"<ZkSyncLiteTransaction(id={self.identifier}, tx_hash='{self.tx_hash}', type='{self.type}')>"


class ZkSyncLiteSwap(Base):
    """Model for ZkSync Lite swaps table"""
    __tablename__ = 'zksynclite_swaps'
    
    tx_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('zksynclite_transactions.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    from_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        nullable=False,
    )
    from_amount: Mapped[str] = mapped_column(FValType, nullable=False)
    to_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        nullable=False,
    )
    to_amount: Mapped[str] = mapped_column(FValType, nullable=False)
    
    # Relationships
    transaction: Mapped['ZkSyncLiteTransaction'] = relationship(back_populates='swap')
    from_asset_ref: Mapped['Asset'] = relationship(foreign_keys=[from_asset])
    to_asset_ref: Mapped['Asset'] = relationship(foreign_keys=[to_asset])
    
    def __repr__(self) -> str:
        return f"<ZkSyncLiteSwap(tx_id={self.tx_id}, from={self.from_asset}, to={self.to_asset})>"