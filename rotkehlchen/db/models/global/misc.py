"""Miscellaneous models for global database using SQLModel"""

from typing import Optional

from sqlalchemy import TEXT, VARCHAR, Column
from sqlmodel import Field

from rotkehlchen.db.models.global.base import Base


class GlobalAddressBook(Base, table=True):
    """Model for global address book table"""
    __tablename__ = 'address_book'

    name: str = Field(sa_column=Column(TEXT, nullable=False))
    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    blockchain: Optional[str] = Field(
        default=None,
        sa_column=Column(VARCHAR(24), primary_key=True)
    )

    def __repr__(self) -> str:
        return f"<GlobalAddressBook(address='{self.address}', name='{self.name}')>"


class BinancePair(Base, table=True):
    """Model for Binance pairs table"""
    __tablename__ = 'binance_pairs'

    pair: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    base_asset: str = Field(sa_column=Column(TEXT, nullable=False))
    quote_asset: str = Field(sa_column=Column(TEXT, nullable=False))
    location: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<BinancePair(pair='{self.pair}', base='{self.base_asset}', quote='{self.quote_asset}')>"