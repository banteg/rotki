"""Enum tables for global database using SQLModel"""

from sqlalchemy import CHAR, VARCHAR, Column
from sqlmodel import Field

from rotkehlchen.db.models.global.base import Base


class AssetType(Base, table=True):
    """Model for asset types enum table"""
    __tablename__ = 'asset_types'

    type: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    seq: int = Field(sa_column=Column(VARCHAR(10), nullable=False))

    def __repr__(self) -> str:
        return f"<AssetType(type='{self.type}', seq={self.seq})>"


class TokenKind(Base, table=True):
    """Model for token kinds enum table"""
    __tablename__ = 'token_kinds'

    kind: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    seq: int = Field(sa_column=Column(VARCHAR(10), nullable=False))

    def __repr__(self) -> str:
        return f"<TokenKind(kind='{self.kind}', seq={self.seq})>"


class PriceHistorySourceType(Base, table=True):
    """Model for price history source types enum table"""
    __tablename__ = 'price_history_source_types'

    type: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    seq: int = Field(sa_column=Column(VARCHAR(10), nullable=False))

    def __repr__(self) -> str:
        return f"<PriceHistorySourceType(type='{self.type}', seq={self.seq})>"