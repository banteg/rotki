"""DeFi protocol-related models for user database using SQLModel"""

from typing import Optional

from sqlalchemy import INTEGER, TEXT, Column, ForeignKey
from sqlmodel import Field

from rotkehlchen.db.orm.types import FValType, TimestampType
from rotkehlchen.db.orm.userdb.base import Base


class CowswapOrder(Base, table=True):
    """Model for CoWSwap orders table"""
    __tablename__ = 'cowswap_orders'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    order_type: str = Field(sa_column=Column(TEXT, nullable=False))
    raw_fee_amount: str = Field(sa_column=Column(FValType, nullable=False))
    sell_token: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    buy_token: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    sell_amount: str = Field(sa_column=Column(FValType, nullable=False))
    buy_amount: str = Field(sa_column=Column(FValType, nullable=False))
    limit_price: Optional[str] = Field(default=None, sa_column=Column(FValType))
    fee_amount: str = Field(sa_column=Column(FValType, nullable=False))
    settlement_contract_address: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<CowswapOrder(identifier='{self.identifier}')>"


class GnosisPayData(Base, table=True):
    """Model for Gnosis Pay data table"""
    __tablename__ = 'gnosispay_data'

    tx_hash: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    merchant_name: str = Field(sa_column=Column(TEXT, nullable=False))
    merchant_city: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    country: str = Field(sa_column=Column(TEXT, nullable=False))
    mcc: int = Field(sa_column=Column(INTEGER, nullable=False))
    amount_in_eur: str = Field(sa_column=Column(FValType, nullable=False))

    def __repr__(self) -> str:
        return f"<GnosisPayData(tx_hash='{self.tx_hash}', merchant='{self.merchant_name}')>"