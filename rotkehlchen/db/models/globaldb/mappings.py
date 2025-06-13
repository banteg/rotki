"""Mapping-related models for global database using SQLModel"""


from sqlalchemy import CHAR, TEXT, Column
from sqlmodel import Field

from rotkehlchen.db.models.globaldb.base import Base


class LocationAssetMapping(Base, table=True):
    """Model for location asset mappings table"""
    __tablename__ = 'location_asset_mappings'

    location: str | None = Field(default=None, sa_column=Column(TEXT, primary_key=True, nullable=True))
    exchange_symbol: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    local_id: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<LocationAssetMapping(location='{self.location}', symbol='{self.exchange_symbol}', local_id='{self.local_id}')>"


class LocationUnsupportedAsset(Base, table=True):
    """Model for location unsupported assets table"""
    __tablename__ = 'location_unsupported_assets'

    location: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    exchange_symbol: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    def __repr__(self) -> str:
        return f"<LocationUnsupportedAsset(location='{self.location}', symbol='{self.exchange_symbol}')>"


class CounterpartyAssetMapping(Base, table=True):
    """Model for counterparty asset mappings table"""
    __tablename__ = 'counterparty_asset_mappings'

    counterparty: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    symbol: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    local_id: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<CounterpartyAssetMapping(counterparty='{self.counterparty}', symbol='{self.symbol}')>"
