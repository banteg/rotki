"""DeFi protocol-related models for user database using SQLModel"""


from sqlalchemy import BLOB, INTEGER, TEXT, Column
from sqlmodel import Field

from rotkehlchen.db.models.types import TimestampType
from rotkehlchen.db.models.user.base import Base


class CowswapOrder(Base, table=True):
    """Model for CoWSwap orders table"""
    __tablename__ = 'cowswap_orders'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    order_type: str = Field(sa_column=Column(TEXT, nullable=False))
    raw_fee_amount: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<CowswapOrder(identifier='{self.identifier}')>"


class GnosisPayData(Base, table=True):
    """Model for Gnosis Pay data table"""
    __tablename__ = 'gnosispay_data'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    tx_hash: bytes = Field(sa_column=Column(BLOB, unique=True, nullable=False))
    timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    merchant_name: str = Field(sa_column=Column(TEXT, nullable=False))
    merchant_city: str | None = Field(default=None, sa_column=Column(TEXT))
    country: str = Field(sa_column=Column(TEXT, nullable=False))
    mcc: int = Field(sa_column=Column(INTEGER, nullable=False))
    transaction_symbol: str = Field(sa_column=Column(TEXT, nullable=False))
    transaction_amount: str = Field(sa_column=Column(TEXT, nullable=False))
    billing_symbol: str | None = Field(default=None, sa_column=Column(TEXT))
    billing_amount: str | None = Field(default=None, sa_column=Column(TEXT))
    reversal_symbol: str | None = Field(default=None, sa_column=Column(TEXT))
    reversal_amount: str | None = Field(default=None, sa_column=Column(TEXT))
    reversal_tx_hash: bytes | None = Field(default=None, sa_column=Column(BLOB, unique=True))

    def __repr__(self) -> str:
        return f"<GnosisPayData(identifier={self.identifier}, merchant='{self.merchant_name}')>"
