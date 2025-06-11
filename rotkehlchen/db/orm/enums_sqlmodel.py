"""SQLModel models for enum tables used in rotkehlchen"""

from typing import Optional

from sqlalchemy import Column, CHAR, INTEGER
from sqlmodel import Field

from rotkehlchen.db.orm.base_sqlmodel import UserDBBase, GlobalDBBase


class Location(UserDBBase, table=True):
    """Model for location enum table"""
    __tablename__ = 'location'
    
    location: str = Field(
        sa_column=Column(CHAR(1), primary_key=True, nullable=False)
    )
    seq: Optional[int] = Field(
        sa_column=Column(INTEGER, unique=True)
    )

    def __repr__(self) -> str:
        return f"<Location(location='{self.location}', seq={self.seq})>"


class BalanceCategory(UserDBBase, table=True):
    """Model for balance category enum table"""
    __tablename__ = 'balance_category'
    
    category: str = Field(
        sa_column=Column(CHAR(1), primary_key=True, nullable=False)
    )
    seq: Optional[int] = Field(
        sa_column=Column(INTEGER, unique=True)
    )

    def __repr__(self) -> str:
        return f"<BalanceCategory(category='{self.category}', seq={self.seq})>"


class ZkSyncLiteTxType(UserDBBase, table=True):
    """Model for zkSync Lite transaction type enum table"""
    __tablename__ = 'zksynclite_tx_type'
    
    type: str = Field(
        sa_column=Column(CHAR(1), primary_key=True, nullable=False)
    )
    seq: Optional[int] = Field(
        sa_column=Column(INTEGER, unique=True)
    )

    def __repr__(self) -> str:
        return f"<ZkSyncLiteTxType(type='{self.type}', seq={self.seq})>"


# Global database enums

class AssetType(GlobalDBBase, table=True):
    """Model for asset type enum table (global database)"""
    __tablename__ = 'asset_types'
    
    type: str = Field(
        sa_column=Column(CHAR(1), primary_key=True, nullable=False)
    )
    seq: Optional[int] = Field(
        sa_column=Column(INTEGER, unique=True)
    )

    def __repr__(self) -> str:
        return f"<AssetType(type='{self.type}', seq={self.seq})>"


class TokenKind(GlobalDBBase, table=True):
    """Model for token kind enum table (global database)"""
    __tablename__ = 'token_kinds'
    
    token_kind: str = Field(
        sa_column=Column(CHAR(1), primary_key=True, nullable=False)
    )
    seq: Optional[int] = Field(
        sa_column=Column(INTEGER, unique=True)
    )

    def __repr__(self) -> str:
        return f"<TokenKind(token_kind='{self.token_kind}', seq={self.seq})>"


class PriceHistorySourceType(GlobalDBBase, table=True):
    """Model for price history source type enum table (global database)"""
    __tablename__ = 'price_history_source_types'
    
    type: str = Field(
        sa_column=Column(CHAR(1), primary_key=True, nullable=False)
    )
    seq: Optional[int] = Field(
        sa_column=Column(INTEGER, unique=True)
    )

    def __repr__(self) -> str:
        return f"<PriceHistorySourceType(type='{self.type}', seq={self.seq})>"