"""SQLAlchemy models for protocol-specific tables"""

from typing import Optional

from sqlalchemy import (
    BLOB, INTEGER, TEXT, Column, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import FValType, HexBytesType, TimestampType


class CowswapOrder(Base):
    """Model for Cowswap orders table"""
    __tablename__ = 'cowswap_orders'
    
    identifier: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    order_type: Mapped[str] = mapped_column(TEXT, nullable=False)
    raw_fee_amount: Mapped[str] = mapped_column(FValType, nullable=False)
    
    def __repr__(self) -> str:
        return f"<CowswapOrder(identifier='{self.identifier}', type='{self.order_type}')>"


class GnosisPayData(Base):
    """Model for Gnosis Pay data table"""
    __tablename__ = 'gnosispay_data'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    tx_hash: Mapped[bytes] = mapped_column(HexBytesType, unique=True, nullable=False)
    timestamp: Mapped[int] = mapped_column(TimestampType, nullable=False)
    merchant_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    merchant_city: Mapped[Optional[str]] = mapped_column(TEXT)
    country: Mapped[str] = mapped_column(TEXT, nullable=False)
    mcc: Mapped[int] = mapped_column(INTEGER, nullable=False)
    transaction_symbol: Mapped[str] = mapped_column(TEXT, nullable=False)
    transaction_amount: Mapped[str] = mapped_column(FValType, nullable=False)
    billing_symbol: Mapped[Optional[str]] = mapped_column(TEXT)
    billing_amount: Mapped[Optional[str]] = mapped_column(FValType)
    reversal_symbol: Mapped[Optional[str]] = mapped_column(TEXT)
    reversal_amount: Mapped[Optional[str]] = mapped_column(FValType)
    reversal_tx_hash: Mapped[Optional[bytes]] = mapped_column(HexBytesType, unique=True)
    
    def __repr__(self) -> str:
        return f"<GnosisPayData(id={self.identifier}, merchant='{self.merchant_name}')>"