"""Mapping-related models for global database using SQLModel"""

from typing import Optional

from sqlalchemy import CHAR, TEXT, VARCHAR, Column, ForeignKey, UniqueConstraint
from sqlmodel import Field

from rotkehlchen.db.models.global.base import Base


class LocationAssetMapping(Base, table=True):
    """Model for location asset mappings table"""
    __tablename__ = 'location_asset_mappings'
    __table_args__ = (
        UniqueConstraint('location', 'location_symbol'),
    )

    location: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    location_symbol: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            nullable=False,
        )
    )

    def __repr__(self) -> str:
        return f"<LocationAssetMapping(location='{self.location}', symbol='{self.location_symbol}', asset='{self.asset}')>"


class LocationUnsupportedAsset(Base, table=True):
    """Model for location unsupported assets table"""
    __tablename__ = 'location_unsupported_assets'

    location: str = Field(sa_column=Column(CHAR(1), primary_key=True, nullable=False))
    location_symbol: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    def __repr__(self) -> str:
        return f"<LocationUnsupportedAsset(location='{self.location}', symbol='{self.location_symbol}')>"


class CounterpartyAssetMapping(Base, table=True):
    """Model for counterparty asset mappings table"""
    __tablename__ = 'counterparty_asset_mappings'

    counterparty_id: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    counterparty_asset_id: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    asset_id: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            nullable=False,
        )
    )

    def __repr__(self) -> str:
        return f"<CounterpartyAssetMapping(counterparty='{self.counterparty_id}', asset='{self.asset_id}')>"