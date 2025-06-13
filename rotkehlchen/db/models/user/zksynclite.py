"""zkSync Lite models for user database"""

from typing import Optional

from sqlalchemy import BLOB, CHAR, INTEGER, TEXT, CheckConstraint, Column, ForeignKey
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.user.base import Base


class ZkSyncLiteTransaction(Base, table=True):
    """Model for zksynclite_transactions table"""
    __tablename__ = 'zksynclite_transactions'
    __table_args__ = (
        CheckConstraint('is_decoded IN (0, 1)'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    tx_hash: bytes = Field(sa_column=Column(BLOB, unique=True, nullable=False))
    type: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('zksynclite_tx_type.type'),
            nullable=False,
            server_default='A',
        ),
    )
    is_decoded: int = Field(sa_column=Column(INTEGER, nullable=False, server_default='0'))
    timestamp: int = Field(sa_column=Column(INTEGER, nullable=False))
    block_number: int = Field(sa_column=Column(INTEGER, nullable=False))
    from_address: str = Field(sa_column=Column(TEXT, nullable=False))
    to_address: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        ),
    )
    amount: str = Field(sa_column=Column(TEXT, nullable=False))
    fee: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

    # Relationships
    type_obj: Optional['ZkSyncLiteTxType'] = Relationship()
    asset_obj: Optional['Asset'] = Relationship(back_populates='zksynclite_transactions')
    swaps: list['ZkSyncLiteSwap'] = Relationship(back_populates='transaction')

    def __repr__(self) -> str:
        return f'<ZkSyncLiteTransaction(identifier={self.identifier}, tx_hash={self.tx_hash.hex()})>'


class ZkSyncLiteSwap(Base, table=True):
    """Model for zksynclite_swaps table"""
    __tablename__ = 'zksynclite_swaps'

    tx_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('zksynclite_transactions.identifier', onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    from_asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        ),
    )
    from_amount: str = Field(sa_column=Column(TEXT, nullable=False))
    to_asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        ),
    )
    to_amount: str = Field(sa_column=Column(TEXT, nullable=False))

    # Relationships
    transaction: 'ZkSyncLiteTransaction' = Relationship(back_populates='swaps')
    from_asset_obj: Optional['Asset'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[ZkSyncLiteSwap.from_asset]'},
    )
    to_asset_obj: Optional['Asset'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[ZkSyncLiteSwap.to_asset]'},
    )

    def __repr__(self) -> str:
        return f"<ZkSyncLiteSwap(tx_id={self.tx_id}, from_asset='{self.from_asset}', to_asset='{self.to_asset}')>"
