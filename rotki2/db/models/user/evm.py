"""EVM-related models for user database"""

from typing import Optional

from sqlalchemy import (
    BLOB,
    INTEGER,
    TEXT,
    CheckConstraint,
    Column,
    ForeignKey,
    UniqueConstraint,
)
from sqlmodel import Field, Relationship

from rotki2.db.models.user.base import Base


class EvmTransaction(Base, table=True):
    """Model for evm_transactions table"""
    __tablename__ = 'evm_transactions'
    __table_args__ = (
        UniqueConstraint('tx_hash', 'chain_id'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    tx_hash: bytes = Field(sa_column=Column(BLOB, nullable=False))
    chain_id: int = Field(sa_column=Column(INTEGER, nullable=False))
    timestamp: int = Field(sa_column=Column(INTEGER, nullable=False))
    block_number: int = Field(sa_column=Column(INTEGER, nullable=False))
    from_address: str = Field(sa_column=Column(TEXT, nullable=False))
    to_address: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    gas: str = Field(sa_column=Column(TEXT, nullable=False))
    gas_price: str = Field(sa_column=Column(TEXT, nullable=False))
    gas_used: str = Field(sa_column=Column(TEXT, nullable=False))
    input_data: bytes = Field(sa_column=Column(BLOB, nullable=False))
    nonce: int = Field(sa_column=Column(INTEGER, nullable=False))

    # Relationships
    receipts: list['EvmTxReceipt'] = Relationship(back_populates='transaction')
    internal_transactions: list['EvmInternalTransaction'] = Relationship(back_populates='transaction')
    tx_mappings: list['EvmTxMapping'] = Relationship(back_populates='transaction')
    address_mappings: list['EvmTxAddressMapping'] = Relationship(back_populates='transaction')
    optimism_transaction: Optional['OptimismTransaction'] = Relationship(back_populates='transaction')

    def __repr__(self) -> str:
        return f'<EvmTransaction(identifier={self.identifier}, tx_hash={self.tx_hash.hex()}, chain_id={self.chain_id})>'


class EvmTxReceipt(Base, table=True):
    """Model for evmtx_receipts table"""
    __tablename__ = 'evmtx_receipts'
    __table_args__ = (
        CheckConstraint('status IN (0, 1)'),
    )

    tx_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('evm_transactions.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    contract_address: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))
    status: int = Field(sa_column=Column(INTEGER, nullable=False))
    type: int = Field(sa_column=Column(INTEGER, nullable=False))

    # Relationships
    transaction: 'EvmTransaction' = Relationship(back_populates='receipts')
    logs: list['EvmTxReceiptLog'] = Relationship(back_populates='receipt')

    def __repr__(self) -> str:
        return f'<EvmTxReceipt(tx_id={self.tx_id}, status={self.status})>'


class EvmTxReceiptLog(Base, table=True):
    """Model for evmtx_receipt_logs table"""
    __tablename__ = 'evmtx_receipt_logs'
    __table_args__ = (
        UniqueConstraint('tx_id', 'log_index'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    tx_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('evmtx_receipts.tx_id', ondelete='CASCADE', onupdate='CASCADE'),
            nullable=False,
        ),
    )
    log_index: int = Field(sa_column=Column(INTEGER, nullable=False))
    data: bytes = Field(sa_column=Column(BLOB, nullable=False))
    address: str = Field(sa_column=Column(TEXT, nullable=False))

    # Relationships
    receipt: 'EvmTxReceipt' = Relationship(back_populates='logs')
    topics: list['EvmTxReceiptLogTopic'] = Relationship(back_populates='log')

    def __repr__(self) -> str:
        return f'<EvmTxReceiptLog(identifier={self.identifier}, log_index={self.log_index})>'


class EvmTxReceiptLogTopic(Base, table=True):
    """Model for evmtx_receipt_log_topics table"""
    __tablename__ = 'evmtx_receipt_log_topics'

    log: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('evmtx_receipt_logs.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    topic: bytes = Field(sa_column=Column(BLOB, nullable=False))
    topic_index: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))

    # Relationships
    log_obj: 'EvmTxReceiptLog' = Relationship(back_populates='topics')

    def __repr__(self) -> str:
        return f'<EvmTxReceiptLogTopic(log={self.log}, topic_index={self.topic_index})>'


class EvmInternalTransaction(Base, table=True):
    """Model for evm_internal_transactions table"""
    __tablename__ = 'evm_internal_transactions'

    parent_tx: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('evm_transactions.identifier', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    trace_id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    from_address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    to_address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    gas: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    gas_used: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    # Relationships
    transaction: 'EvmTransaction' = Relationship(back_populates='internal_transactions')

    def __repr__(self) -> str:
        return f'<EvmInternalTransaction(parent_tx={self.parent_tx}, trace_id={self.trace_id})>'


class EvmTxMapping(Base, table=True):
    """Model for evm_tx_mappings table"""
    __tablename__ = 'evm_tx_mappings'

    tx_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('evm_transactions.identifier', onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    value: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))

    # Relationships
    transaction: 'EvmTransaction' = Relationship(back_populates='tx_mappings')

    def __repr__(self) -> str:
        return f'<EvmTxMapping(tx_id={self.tx_id}, value={self.value})>'


class EvmTxAddressMapping(Base, table=True):
    """Model for evmtx_address_mappings table"""
    __tablename__ = 'evmtx_address_mappings'

    tx_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('evm_transactions.identifier', onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    # Relationships
    transaction: 'EvmTransaction' = Relationship(back_populates='address_mappings')

    def __repr__(self) -> str:
        return f"<EvmTxAddressMapping(tx_id={self.tx_id}, address='{self.address}')>"


class OptimismTransaction(Base, table=True):
    """Model for optimism_transactions table"""
    __tablename__ = 'optimism_transactions'

    tx_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('evm_transactions.identifier', onupdate='CASCADE', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    l1_fee: str | None = Field(default=None, sa_column=Column(TEXT, nullable=True))

    # Relationships
    transaction: 'EvmTransaction' = Relationship(back_populates='optimism_transaction')

    def __repr__(self) -> str:
        return f"<OptimismTransaction(tx_id={self.tx_id}, l1_fee='{self.l1_fee}')>"


class EvmTransactionAuthorization(Base, table=True):
    """Model for evm_transactions_authorizations table"""
    __tablename__ = 'evm_transactions_authorizations'

    tx_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('evm_transactions.identifier', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        ),
    )
    nonce: int = Field(sa_column=Column(INTEGER, nullable=False))
    delegated_address: str = Field(sa_column=Column(TEXT, nullable=False))

    # Relationships
    transaction: 'EvmTransaction' = Relationship()

    def __repr__(self) -> str:
        return f'<EvmTransactionAuthorization(tx_id={self.tx_id}, nonce={self.nonce})>'
