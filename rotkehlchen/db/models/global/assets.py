"""Asset-related models for global database using SQLModel"""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    CHAR, INTEGER, TEXT, Column, ForeignKey, Index, UniqueConstraint
)
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.types import BooleanType, FValType, TimestampType
from rotkehlchen.db.models.global.base import Base

if TYPE_CHECKING:
    from rotkehlchen.db.models.global.enums import AssetType, TokenKind


class GlobalAsset(Base, table=True):
    """Model for assets table in global database"""
    __tablename__ = 'assets'
    __table_args__ = (
        Index('idx_assets_identifier', 'identifier'),
    )

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    name: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    type: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('asset_types.type'),
            nullable=False,
            server_default='A',
        )
    )

    # Relationships
    type_ref: Optional['AssetType'] = Relationship()
    common_details: Optional['CommonAssetDetails'] = Relationship(
        back_populates='asset',
        cascade_delete=True,
        sa_relationship_kwargs={'uselist': False},
    )
    evm_token: Optional['EvmToken'] = Relationship(
        back_populates='asset',
        cascade_delete=True,
        sa_relationship_kwargs={'uselist': False},
    )
    custom_asset: Optional['CustomAsset'] = Relationship(
        back_populates='asset',
        cascade_delete=True,
        sa_relationship_kwargs={'uselist': False},
    )
    collection_main: Optional['AssetCollection'] = Relationship(
        back_populates='main_asset_ref',
        sa_relationship_kwargs={'uselist': False},
    )
    multiasset_mappings: List['MultiassetMapping'] = Relationship(
        back_populates='asset_ref',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<GlobalAsset(identifier='{self.identifier}', type='{self.type}')>"


class CommonAssetDetails(Base, table=True):
    """Model for common asset details table"""
    __tablename__ = 'common_asset_details'

    identifier: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    symbol: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    coingecko: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    cryptocompare: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    forked: Optional[str] = Field(
        default=None,
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='SET NULL', onupdate='CASCADE'),
        )
    )
    started: Optional[int] = Field(default=None, sa_column=Column(TimestampType))
    swapped_for: Optional[str] = Field(
        default=None,
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='SET NULL', onupdate='CASCADE'),
        )
    )

    # Relationships
    asset: Optional['GlobalAsset'] = Relationship(back_populates='common_details')
    forked_from: Optional['GlobalAsset'] = Relationship(
        sa_relationship_kwargs={
            'foreign_keys': '[CommonAssetDetails.forked]',
            'remote_side': '[GlobalAsset.identifier]',
        }
    )
    swapped_for_asset: Optional['GlobalAsset'] = Relationship(
        sa_relationship_kwargs={
            'foreign_keys': '[CommonAssetDetails.swapped_for]',
            'remote_side': '[GlobalAsset.identifier]',
        }
    )

    def __repr__(self) -> str:
        return f"<CommonAssetDetails(identifier='{self.identifier}', symbol='{self.symbol}')>"


class EvmToken(Base, table=True):
    """Model for EVM tokens table"""
    __tablename__ = 'evm_tokens'

    identifier: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    token_kind: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('token_kinds.kind'),
            nullable=False,
            server_default='A',
        )
    )
    chain: int = Field(sa_column=Column(INTEGER, nullable=False))
    address: str = Field(sa_column=Column(TEXT, nullable=False))
    decimals: Optional[int] = Field(default=None, sa_column=Column(INTEGER))
    protocol: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    asset: Optional['GlobalAsset'] = Relationship(back_populates='evm_token')
    token_kind_ref: Optional['TokenKind'] = Relationship()
    underlying_tokens: List['UnderlyingTokensList'] = Relationship(
        back_populates='parent_token',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<EvmToken(identifier='{self.identifier}', chain={self.chain}, address='{self.address}')>"


class CustomAsset(Base, table=True):
    """Model for custom assets table"""
    __tablename__ = 'custom_assets'

    identifier: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    notes: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    type: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('asset_types.type'),
            nullable=False,
        )
    )

    # Relationships
    asset: Optional['GlobalAsset'] = Relationship(back_populates='custom_asset')
    type_ref: Optional['AssetType'] = Relationship()

    def __repr__(self) -> str:
        return f"<CustomAsset(identifier='{self.identifier}', type='{self.type}')>"


class AssetCollection(Base, table=True):
    """Model for asset collections table"""
    __tablename__ = 'asset_collections'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    name: str = Field(sa_column=Column(TEXT, nullable=False))
    main_asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            nullable=False,
        )
    )

    # Relationships
    main_asset_ref: Optional['GlobalAsset'] = Relationship(back_populates='collection_main')

    def __repr__(self) -> str:
        return f"<AssetCollection(id={self.id}, name='{self.name}', main_asset='{self.main_asset}')>"


class MultiassetMapping(Base, table=True):
    """Model for multiasset mappings table"""
    __tablename__ = 'multiasset_mappings'

    asset: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    collection_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('asset_collections.id', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )

    # Relationships
    asset_ref: Optional['GlobalAsset'] = Relationship(back_populates='multiasset_mappings')
    collection: Optional['AssetCollection'] = Relationship()

    def __repr__(self) -> str:
        return f"<MultiassetMapping(asset='{self.asset}', collection_id={self.collection_id})>"


class UnderlyingTokensList(Base, table=True):
    """Model for underlying tokens list table"""
    __tablename__ = 'underlying_tokens_list'

    identifier: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('evm_tokens.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    weight: str = Field(sa_column=Column(FValType, primary_key=True, nullable=False))
    underlying_token: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('evm_tokens.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )

    # Relationships
    parent_token: Optional['EvmToken'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[UnderlyingTokensList.identifier]'},
        back_populates='underlying_tokens',
    )
    underlying: Optional['EvmToken'] = Relationship(
        sa_relationship_kwargs={'foreign_keys': '[UnderlyingTokensList.underlying_token]'}
    )

    def __repr__(self) -> str:
        return f"<UnderlyingTokensList(identifier='{self.identifier}', underlying='{self.underlying_token}')>"


class UserOwnedAsset(Base, table=True):
    """Model for user owned assets table"""
    __tablename__ = 'user_owned_assets'

    asset_id: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )

    def __repr__(self) -> str:
        return f"<UserOwnedAsset(asset_id='{self.asset_id}')>"