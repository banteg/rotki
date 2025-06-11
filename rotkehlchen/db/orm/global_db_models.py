"""SQLAlchemy models for global database tables"""

from typing import Optional

from sqlalchemy import (
    CHAR, INTEGER, TEXT, VARCHAR, Column, ForeignKey, UniqueConstraint,
    CheckConstraint, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import BooleanType, FValType, TimestampType


# Asset related models

class GlobalAsset(Base):
    """Model for assets table in global database"""
    __tablename__ = 'assets'
    
    identifier: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    type: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('asset_types.type'),
        nullable=False,
        default='A',
    )
    
    # Relationships
    type_ref: Mapped['AssetType'] = relationship()
    common_details: Mapped[Optional['CommonAssetDetails']] = relationship(
        back_populates='asset',
        cascade='all, delete-orphan',
        uselist=False,
    )
    evm_token: Mapped[Optional['EvmToken']] = relationship(
        back_populates='asset',
        cascade='all, delete-orphan',
        uselist=False,
    )
    custom_asset: Mapped[Optional['CustomAsset']] = relationship(
        back_populates='asset',
        cascade='all, delete-orphan',
        uselist=False,
    )
    collection_main: Mapped[Optional['AssetCollection']] = relationship(
        back_populates='main_asset_ref',
        uselist=False,
    )
    multiasset_mappings: Mapped[list['MultiassetMapping']] = relationship(
        back_populates='asset_ref',
        cascade='all, delete-orphan',
    )
    
    __table_args__ = (
        Index('idx_assets_identifier', 'identifier'),
    )
    
    def __repr__(self) -> str:
        return f"<GlobalAsset(identifier='{self.identifier}', type='{self.type}')>"


class CommonAssetDetails(Base):
    """Model for common asset details table"""
    __tablename__ = 'common_asset_details'
    
    identifier: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    symbol: Mapped[Optional[str]] = mapped_column(TEXT)
    coingecko: Mapped[Optional[str]] = mapped_column(TEXT)
    cryptocompare: Mapped[Optional[str]] = mapped_column(TEXT)
    forked: Mapped[Optional[str]] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='SET NULL', onupdate='CASCADE'),
    )
    started: Mapped[Optional[int]] = mapped_column(TimestampType)
    swapped_for: Mapped[Optional[str]] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='SET NULL', onupdate='CASCADE'),
    )
    
    # Relationships
    asset: Mapped['GlobalAsset'] = relationship(back_populates='common_details')
    forked_from: Mapped[Optional['GlobalAsset']] = relationship(
        foreign_keys=[forked],
        remote_side='GlobalAsset.identifier',
    )
    swapped_for_asset: Mapped[Optional['GlobalAsset']] = relationship(
        foreign_keys=[swapped_for],
        remote_side='GlobalAsset.identifier',
    )
    
    __table_args__ = (
        Index('idx_common_assets_identifier', 'identifier'),
    )
    
    def __repr__(self) -> str:
        return f"<CommonAssetDetails(identifier='{self.identifier}', symbol='{self.symbol}')>"


class EvmToken(Base):
    """Model for EVM tokens table"""
    __tablename__ = 'evm_tokens'
    
    identifier: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    token_kind: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('token_kinds.token_kind'),
        nullable=False,
        default='A',
    )
    chain: Mapped[int] = mapped_column(INTEGER, nullable=False)
    address: Mapped[str] = mapped_column(VARCHAR(42), nullable=False)
    decimals: Mapped[Optional[int]] = mapped_column(INTEGER)
    protocol: Mapped[Optional[str]] = mapped_column(TEXT)
    
    # Relationships
    asset: Mapped['GlobalAsset'] = relationship(back_populates='evm_token')
    token_kind_ref: Mapped['TokenKind'] = relationship()
    underlying_tokens: Mapped[list['UnderlyingTokensList']] = relationship(
        foreign_keys='UnderlyingTokensList.parent_token_entry',
        back_populates='parent_token',
        cascade='all, delete-orphan',
    )
    
    __table_args__ = (
        Index('idx_evm_tokens_identifier', 'identifier', 'chain', 'protocol'),
    )
    
    def __repr__(self) -> str:
        return f"<EvmToken(identifier='{self.identifier}', chain={self.chain}, address='{self.address}')>"


class UnderlyingTokensList(Base):
    """Model for underlying tokens list table"""
    __tablename__ = 'underlying_tokens_list'
    
    identifier: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('evm_tokens.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    weight: Mapped[str] = mapped_column(FValType, nullable=False)
    parent_token_entry: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('evm_tokens.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    
    # Relationships
    token: Mapped['EvmToken'] = relationship(foreign_keys=[identifier])
    parent_token: Mapped['EvmToken'] = relationship(foreign_keys=[parent_token_entry])
    
    __table_args__ = (
        Index('idx_underlying_tokens_lists_identifier', 'identifier', 'parent_token_entry'),
    )
    
    def __repr__(self) -> str:
        return f"<UnderlyingTokensList(token='{self.identifier}', parent='{self.parent_token_entry}')>"


class CustomAsset(Base):
    """Model for custom assets table"""
    __tablename__ = 'custom_assets'
    
    identifier: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(TEXT)
    type: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    # Relationships
    asset: Mapped['GlobalAsset'] = relationship(back_populates='custom_asset')
    
    def __repr__(self) -> str:
        return f"<CustomAsset(identifier='{self.identifier}', type='{self.type}')>"


class AssetCollection(Base):
    """Model for asset collections table"""
    __tablename__ = 'asset_collections'
    
    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    symbol: Mapped[str] = mapped_column(TEXT, nullable=False)
    main_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        unique=True,
        nullable=False,
    )
    
    # Relationships
    main_asset_ref: Mapped['GlobalAsset'] = relationship(back_populates='collection_main')
    mappings: Mapped[list['MultiassetMapping']] = relationship(
        back_populates='collection',
        cascade='all, delete-orphan',
    )
    
    __table_args__ = (
        UniqueConstraint('name', 'symbol'),
        Index('idx_asset_collections_main_asset', 'main_asset'),
    )
    
    def __repr__(self) -> str:
        return f"<AssetCollection(id={self.id}, name='{self.name}', symbol='{self.symbol}')>"


class MultiassetMapping(Base):
    """Model for multiasset mappings table"""
    __tablename__ = 'multiasset_mappings'
    
    collection_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('asset_collections.id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    
    # Relationships
    collection: Mapped['AssetCollection'] = relationship(back_populates='mappings')
    asset_ref: Mapped['GlobalAsset'] = relationship(back_populates='multiasset_mappings')
    
    __table_args__ = (
        Index('idx_multiasset_mappings_asset', 'asset'),
        Index('idx_multiasset_mappings_identifier', 'asset'),
    )
    
    def __repr__(self) -> str:
        return f"<MultiassetMapping(collection_id={self.collection_id}, asset='{self.asset}')>"


class UserOwnedAsset(Base):
    """Model for user owned assets table"""
    __tablename__ = 'user_owned_assets'
    
    asset_id: Mapped[str] = mapped_column(
        VARCHAR(24),
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    
    # Relationships
    asset: Mapped['GlobalAsset'] = relationship()
    
    __table_args__ = (
        Index('idx_user_owned_assets_asset_id', 'asset_id'),
    )
    
    def __repr__(self) -> str:
        return f"<UserOwnedAsset(asset_id='{self.asset_id}')>"


# Price related models

class PriceHistory(Base):
    """Model for price history table"""
    __tablename__ = 'price_history'
    
    from_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    to_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('price_history_source_types.type'),
        primary_key=True,
        nullable=False,
        default='A',
    )
    timestamp: Mapped[int] = mapped_column(TimestampType, primary_key=True, nullable=False)
    price: Mapped[str] = mapped_column(FValType, nullable=False)
    
    # Relationships
    from_asset_ref: Mapped['GlobalAsset'] = relationship(foreign_keys=[from_asset])
    to_asset_ref: Mapped['GlobalAsset'] = relationship(foreign_keys=[to_asset])
    source_type_ref: Mapped['PriceHistorySourceType'] = relationship()
    
    __table_args__ = (
        Index('idx_price_history_identifier', 'from_asset', 'to_asset'),
    )
    
    def __repr__(self) -> str:
        return f"<PriceHistory(from='{self.from_asset}', to='{self.to_asset}', timestamp={self.timestamp})>"


# Exchange related models

class BinancePair(Base):
    """Model for Binance pairs table"""
    __tablename__ = 'binance_pairs'
    
    pair: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    base_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,
    )
    quote_asset: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    
    # Relationships
    base_asset_ref: Mapped['GlobalAsset'] = relationship(foreign_keys=[base_asset])
    quote_asset_ref: Mapped['GlobalAsset'] = relationship(foreign_keys=[quote_asset])
    
    __table_args__ = (
        Index('idx_binance_pairs_identifier', 'base_asset', 'quote_asset'),
    )
    
    def __repr__(self) -> str:
        return f"<BinancePair(pair='{self.pair}', location='{self.location}')>"


# Mapping tables

class LocationAssetMapping(Base):
    """Model for location asset mappings table"""
    __tablename__ = 'location_asset_mappings'
    
    location: Mapped[Optional[str]] = mapped_column(TEXT)
    exchange_symbol: Mapped[str] = mapped_column(TEXT, nullable=False)
    local_id: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('location', 'exchange_symbol'),
        Index('idx_location_mappings_identifier', 'local_id'),
    )
    
    def __repr__(self) -> str:
        return f"<LocationAssetMapping(location='{self.location}', symbol='{self.exchange_symbol}')>"


class CounterpartyAssetMapping(Base):
    """Model for counterparty asset mappings table"""
    __tablename__ = 'counterparty_asset_mappings'
    
    counterparty: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    local_id: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    def __repr__(self) -> str:
        return f"<CounterpartyAssetMapping(counterparty='{self.counterparty}', symbol='{self.symbol}')>"


class LocationUnsupportedAsset(Base):
    """Model for location unsupported assets table"""
    __tablename__ = 'location_unsupported_assets'
    
    location: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    exchange_symbol: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('location', 'exchange_symbol'),
    )
    
    def __repr__(self) -> str:
        return f"<LocationUnsupportedAsset(location='{self.location}', symbol='{self.exchange_symbol}')>"


# Other global database models

class GlobalSettings(Base):
    """Model for settings table in global database"""
    __tablename__ = 'settings'
    
    name: Mapped[str] = mapped_column(VARCHAR(24), primary_key=True, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(TEXT)
    
    def __repr__(self) -> str:
        return f"<GlobalSettings(name='{self.name}', value='{self.value}')>"


class GlobalAddressBook(Base):
    """Model for address book table in global database"""
    __tablename__ = 'address_book'
    
    address: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    blockchain: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    def __repr__(self) -> str:
        return f"<GlobalAddressBook(address='{self.address}', name='{self.name}')>"


class DefaultRPCNode(Base):
    """Model for default RPC nodes table"""
    __tablename__ = 'default_rpc_nodes'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    endpoint: Mapped[str] = mapped_column(TEXT, nullable=False)
    owned: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    active: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    weight: Mapped[str] = mapped_column(FValType, nullable=False)
    blockchain: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    __table_args__ = (
        CheckConstraint('owned IN (0, 1)'),
        CheckConstraint('active IN (0, 1)'),
    )
    
    def __repr__(self) -> str:
        return f"<DefaultRPCNode(id={self.identifier}, name='{self.name}', blockchain='{self.blockchain}')>"


class GeneralCache(Base):
    """Model for general cache table"""
    __tablename__ = 'general_cache'
    
    key: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    value: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    last_queried_ts: Mapped[int] = mapped_column(TimestampType, nullable=False)
    
    def __repr__(self) -> str:
        return f"<GeneralCache(key='{self.key}', value='{self.value}')>"


class UniqueCache(Base):
    """Model for unique cache table"""
    __tablename__ = 'unique_cache'
    
    key: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    value: Mapped[str] = mapped_column(TEXT, nullable=False)
    last_queried_ts: Mapped[int] = mapped_column(TimestampType, nullable=False)
    
    def __repr__(self) -> str:
        return f"<UniqueCache(key='{self.key}', value='{self.value}')>"


class ContractABI(Base):
    """Model for contract ABI table"""
    __tablename__ = 'contract_abi'
    
    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    value: Mapped[str] = mapped_column(TEXT, unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(TEXT)
    
    # Relationships
    contracts: Mapped[list['ContractData']] = relationship(
        back_populates='abi_ref',
        cascade='all, delete-orphan',
    )
    
    def __repr__(self) -> str:
        return f"<ContractABI(id={self.id}, name='{self.name}')>"


class ContractData(Base):
    """Model for contract data table"""
    __tablename__ = 'contract_data'
    
    address: Mapped[str] = mapped_column(VARCHAR(42), primary_key=True, nullable=False)
    chain_id: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    abi: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('contract_abi.id', ondelete='SET NULL', onupdate='CASCADE'),
        nullable=False,
    )
    deployed_block: Mapped[Optional[int]] = mapped_column(INTEGER)
    
    # Relationships
    abi_ref: Mapped['ContractABI'] = relationship(back_populates='contracts')
    
    def __repr__(self) -> str:
        return f"<ContractData(address='{self.address}', chain_id={self.chain_id})>"