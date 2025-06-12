"""Enum tables for user database using SQLModel"""

from sqlalchemy import CHAR, INTEGER, VARCHAR, Column
from sqlmodel import Field

from rotkehlchen.db.models.user.base import Base


class Location(Base, table=True):
    """Model for location enum table"""
    __tablename__ = 'location'

    location: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    seq: int | None = Field(default=None, sa_column=Column(INTEGER, nullable=True, unique=True))

    def __repr__(self) -> str:
        return f"<Location(location='{self.location}', seq={self.seq})>"


class BalanceCategory(Base, table=True):
    """Model for balance category enum table"""
    __tablename__ = 'balance_category'

    category: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    seq: int | None = Field(default=None, sa_column=Column(INTEGER, nullable=True, unique=True))

    def __repr__(self) -> str:
        return f"<BalanceCategory(category='{self.category}', seq={self.seq})>"


class ZkSyncLiteTxType(Base, table=True):
    """Model for zkSync Lite transaction type enum table"""
    __tablename__ = 'zksynclite_tx_type'

    type: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    seq: int | None = Field(default=None, sa_column=Column(INTEGER, nullable=True, unique=True))

    def __repr__(self) -> str:
        return f"<ZkSyncLiteTxType(type='{self.type}', seq={self.seq})>"
