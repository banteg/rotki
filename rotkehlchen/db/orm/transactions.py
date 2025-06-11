"""SQLAlchemy models for transaction-related tables"""

from typing import Optional

from sqlalchemy import (
    BLOB, CHAR, INTEGER, TEXT, Column, ForeignKey, UniqueConstraint,
    CheckConstraint, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import (
    BooleanType, FValType, HexBytesType, TimestampType
)


class EvmTransaction(Base):
    """Model for EVM transactions table"""
    __tablename__ = 'evm_transactions'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    tx_hash: Mapped[bytes] = mapped_column(HexBytesType, nullable=False)
    chain_id: Mapped[int] = mapped_column(INTEGER, nullable=False)
    timestamp: Mapped[int] = mapped_column(TimestampType, nullable=False)
    block_number: Mapped[int] = mapped_column(INTEGER, nullable=False)
    from_address: Mapped[str] = mapped_column(TEXT, nullable=False)
    to_address: Mapped[Optional[str]] = mapped_column(TEXT)
    value: Mapped[str] = mapped_column(FValType, nullable=False)
    gas: Mapped[str] = mapped_column(FValType, nullable=False)
    gas_price: Mapped[str] = mapped_column(FValType, nullable=False)
    gas_used: Mapped[str] = mapped_column(FValType, nullable=False)
    input_data: Mapped[bytes] = mapped_column(BLOB, nullable=False)
    nonce: Mapped[int] = mapped_column(INTEGER, nullable=False)
    
    # Relationships
    internal_transactions: Mapped[list['EvmInternalTransaction']] = relationship(
        back_populates='parent_transaction',
        cascade='all, delete-orphan',
    )
    receipt: Mapped[Optional['EvmTxReceipt']] = relationship(
        back_populates='transaction',
        cascade='all, delete-orphan',
        uselist=False,
    )
    optimism_data: Mapped[Optional['OptimismTransaction']] = relationship(
        back_populates='transaction',
        cascade='all, delete-orphan',
        uselist=False,
    )
    address_mappings: Mapped[list['EvmTxAddressMapping']] = relationship(
        back_populates='transaction',
        cascade='all, delete-orphan',
    )
    tx_mappings: Mapped[list['EvmTxMapping']] = relationship(
        back_populates='transaction',
        cascade='all, delete-orphan',
    )
    
    __table_args__ = (
        UniqueConstraint('tx_hash', 'chain_id'),
    )
    
    def __repr__(self) -> str:
        return f"<EvmTransaction(id={self.identifier}, tx_hash='{self.tx_hash}', chain_id={self.chain_id})>"


class EvmInternalTransaction(Base):
    """Model for EVM internal transactions table"""
    __tablename__ = 'evm_internal_transactions'
    
    parent_tx: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('evm_transactions.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    trace_id: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    from_address: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    to_address: Mapped[Optional[str]] = mapped_column(TEXT, primary_key=True)
    value: Mapped[str] = mapped_column(FValType, primary_key=True, nullable=False)
    gas: Mapped[str] = mapped_column(FValType, primary_key=True, nullable=False)
    gas_used: Mapped[str] = mapped_column(FValType, primary_key=True, nullable=False)
    
    # Relationships
    parent_transaction: Mapped['EvmTransaction'] = relationship(back_populates='internal_transactions')
    
    def __repr__(self) -> str:
        return f"<EvmInternalTransaction(parent_tx={self.parent_tx}, trace_id={self.trace_id})>"


class EvmTxReceipt(Base):
    """Model for EVM transaction receipts table"""
    __tablename__ = 'evmtx_receipts'
    
    tx_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('evm_transactions.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    contract_address: Mapped[Optional[str]] = mapped_column(TEXT)
    status: Mapped[int] = mapped_column(INTEGER, nullable=False)
    type: Mapped[int] = mapped_column(INTEGER, nullable=False)
    
    # Relationships
    transaction: Mapped['EvmTransaction'] = relationship(back_populates='receipt')
    logs: Mapped[list['EvmTxReceiptLog']] = relationship(
        back_populates='receipt',
        cascade='all, delete-orphan',
    )
    
    __table_args__ = (
        CheckConstraint('status IN (0, 1)'),
    )
    
    def __repr__(self) -> str:
        return f"<EvmTxReceipt(tx_id={self.tx_id}, status={self.status})>"


class EvmTxReceiptLog(Base):
    """Model for EVM transaction receipt logs table"""
    __tablename__ = 'evmtx_receipt_logs'
    
    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    tx_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('evmtx_receipts.tx_id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,
    )
    log_index: Mapped[int] = mapped_column(INTEGER, nullable=False)
    data: Mapped[bytes] = mapped_column(BLOB, nullable=False)
    address: Mapped[str] = mapped_column(TEXT, nullable=False)
    
    # Relationships
    receipt: Mapped['EvmTxReceipt'] = relationship(back_populates='logs')
    topics: Mapped[list['EvmTxReceiptLogTopic']] = relationship(
        back_populates='log',
        cascade='all, delete-orphan',
    )
    
    __table_args__ = (
        UniqueConstraint('tx_id', 'log_index'),
    )
    
    def __repr__(self) -> str:
        return f"<EvmTxReceiptLog(id={self.identifier}, tx_id={self.tx_id}, log_index={self.log_index})>"


class EvmTxReceiptLogTopic(Base):
    """Model for EVM transaction receipt log topics table"""
    __tablename__ = 'evmtx_receipt_log_topics'
    
    log: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('evmtx_receipt_logs.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    topic: Mapped[bytes] = mapped_column(BLOB, primary_key=True, nullable=False)
    topic_index: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    
    # Relationships
    log_ref: Mapped['EvmTxReceiptLog'] = relationship(back_populates='topics')
    
    def __repr__(self) -> str:
        return f"<EvmTxReceiptLogTopic(log={self.log}, topic_index={self.topic_index})>"


class OptimismTransaction(Base):
    """Model for Optimism-specific transaction data"""
    __tablename__ = 'optimism_transactions'
    
    tx_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('evm_transactions.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    l1_fee: Mapped[Optional[str]] = mapped_column(FValType)
    
    # Relationships
    transaction: Mapped['EvmTransaction'] = relationship(back_populates='optimism_data')
    
    def __repr__(self) -> str:
        return f"<OptimismTransaction(tx_id={self.tx_id}, l1_fee={self.l1_fee})>"


class EvmTxAddressMapping(Base):
    """Model for EVM transaction address mappings table"""
    __tablename__ = 'evmtx_address_mappings'
    
    tx_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('evm_transactions.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    address: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    
    # Relationships
    transaction: Mapped['EvmTransaction'] = relationship(back_populates='address_mappings')
    
    def __repr__(self) -> str:
        return f"<EvmTxAddressMapping(tx_id={self.tx_id}, address='{self.address}')>"


class EvmTxMapping(Base):
    """Model for EVM transaction mappings table (used for decoded status)"""
    __tablename__ = 'evm_tx_mappings'
    
    tx_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('evm_transactions.identifier', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    value: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    
    # Relationships
    transaction: Mapped['EvmTransaction'] = relationship(back_populates='tx_mappings')
    
    def __repr__(self) -> str:
        return f"<EvmTxMapping(tx_id={self.tx_id}, value={self.value})>"