"""SQLAlchemy models for enum tables used in rotkehlchen"""

from sqlalchemy import CHAR, INTEGER, Column, UniqueConstraint
from sqlalchemy.orm import relationship

from rotkehlchen.db.orm.base import Base


class Location(Base):
    """Model for location enum table"""
    __tablename__ = 'location'
    
    location = Column(CHAR(1), primary_key=True, nullable=False)
    seq = Column(INTEGER, unique=True)
    
    def __repr__(self) -> str:
        return f"<Location(location='{self.location}', seq={self.seq})>"


class BalanceCategory(Base):
    """Model for balance category enum table"""
    __tablename__ = 'balance_category'
    
    category = Column(CHAR(1), primary_key=True, nullable=False)
    seq = Column(INTEGER, unique=True)
    
    def __repr__(self) -> str:
        return f"<BalanceCategory(category='{self.category}', seq={self.seq})>"


class ZkSyncLiteTxType(Base):
    """Model for zkSync Lite transaction type enum table"""
    __tablename__ = 'zksynclite_tx_type'
    
    type = Column(CHAR(1), primary_key=True, nullable=False)
    seq = Column(INTEGER, unique=True)
    
    def __repr__(self) -> str:
        return f"<ZkSyncLiteTxType(type='{self.type}', seq={self.seq})>"


# Global database enums

class AssetType(Base):
    """Model for asset type enum table (global database)"""
    __tablename__ = 'asset_types'
    
    type = Column(CHAR(1), primary_key=True, nullable=False)
    seq = Column(INTEGER, unique=True)
    
    def __repr__(self) -> str:
        return f"<AssetType(type='{self.type}', seq={self.seq})>"


class TokenKind(Base):
    """Model for token kind enum table (global database)"""
    __tablename__ = 'token_kinds'
    
    token_kind = Column(CHAR(1), primary_key=True, nullable=False)
    seq = Column(INTEGER, unique=True)
    
    def __repr__(self) -> str:
        return f"<TokenKind(token_kind='{self.token_kind}', seq={self.seq})>"


class PriceHistorySourceType(Base):
    """Model for price history source type enum table (global database)"""
    __tablename__ = 'price_history_source_types'
    
    type = Column(CHAR(1), primary_key=True, nullable=False)
    seq = Column(INTEGER, unique=True)
    
    def __repr__(self) -> str:
        return f"<PriceHistorySourceType(type='{self.type}', seq={self.seq})>"