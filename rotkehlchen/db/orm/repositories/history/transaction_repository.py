"""Repository for EVM transaction management"""


from sqlalchemy import func, or_, select

from rotkehlchen.types import EvmTransaction as EvmTransactionData
from rotkehlchen.db.orm.transactions import (
    EvmInternalTransaction,
    EvmTransaction,
    EvmTxAddressMapping,
    EvmTxMapping,
    EvmTxReceipt,
    EvmTxReceiptLog,
    EvmTxReceiptLogTopic,
    OptimismTransaction,
)
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Timestamp


class EvmTransactionRepository(BaseRepository[EvmTransaction]):
    """Repository for managing EVM transactions"""

    def __init__(self, session):
        super().__init__(session, EvmTransaction)

    def add_transaction(
        self,
        tx_data: EvmTransactionData,
    ) -> EvmTransaction:
        """Add an EVM transaction"""
        tx = EvmTransaction(
            tx_hash=tx_data.tx_hash,
            chain_id=tx_data.chain_id,
            timestamp=int(tx_data.timestamp),
            block_number=tx_data.block_number,
            from_address=tx_data.from_address,
            to_address=tx_data.to_address,
            value=str(tx_data.value),
            gas=str(tx_data.gas),
            gas_price=str(tx_data.gas_price),
            gas_used=str(tx_data.gas_used),
            input_data=tx_data.input_data,
            nonce=tx_data.nonce,
        )
        return self.add(tx)

    def get_transaction(
        self,
        tx_hash: EVMTxHash,
        chain_id: int,
    ) -> EvmTransaction | None:
        """Get a transaction by hash and chain"""
        stmt = select(EvmTransaction).filter_by(
            tx_hash=tx_hash,
            chain_id=chain_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_transactions(
        self,
        address: ChecksumEvmAddress | None = None,
        chain_id: int | None = None,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EvmTransaction]:
        """Get transactions with filters"""
        query = select(EvmTransaction)

        if address:
            # Get transactions where address is from or to
            query = query.filter(
                or_(
                    EvmTransaction.from_address == address,
                    EvmTransaction.to_address == address,
                ),
            )

        if chain_id is not None:
            query = query.filter_by(chain_id=chain_id)

        if from_timestamp is not None:
            query = query.filter(EvmTransaction.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(EvmTransaction.timestamp <= int(to_timestamp))

        # Order by timestamp descending
        query = query.order_by(EvmTransaction.timestamp.desc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def add_receipt(
        self,
        tx_id: int,
        contract_address: ChecksumEvmAddress | None,
        status: int,
        tx_type: int,
    ) -> EvmTxReceipt:
        """Add a transaction receipt"""
        receipt = EvmTxReceipt(
            tx_id=tx_id,
            contract_address=contract_address,
            status=status,
            type=tx_type,
        )
        self.session.add(receipt)
        self.session.flush()
        return receipt

    def add_receipt_log(
        self,
        tx_id: int,
        log_index: int,
        data: bytes,
        address: ChecksumEvmAddress,
        topics: list[bytes],
    ) -> EvmTxReceiptLog:
        """Add a transaction receipt log with topics"""
        log = EvmTxReceiptLog(
            tx_id=tx_id,
            log_index=log_index,
            data=data,
            address=address,
        )
        self.session.add(log)
        self.session.flush()

        # Add topics
        for topic_index, topic in enumerate(topics):
            topic_entry = EvmTxReceiptLogTopic(
                log=log.identifier,
                topic=topic,
                topic_index=topic_index,
            )
            self.session.add(topic_entry)

        self.session.flush()
        return log

    def add_internal_transaction(
        self,
        parent_tx_id: int,
        trace_id: int,
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress | None,
        value: FVal,
        gas: FVal,
        gas_used: FVal,
    ) -> EvmInternalTransaction:
        """Add an internal transaction"""
        internal_tx = EvmInternalTransaction(
            parent_tx=parent_tx_id,
            trace_id=trace_id,
            from_address=from_address,
            to_address=to_address,
            value=str(value),
            gas=str(gas),
            gas_used=str(gas_used),
        )
        self.session.add(internal_tx)
        self.session.flush()
        return internal_tx

    def get_internal_transactions(
        self,
        parent_tx_id: int,
    ) -> list[EvmInternalTransaction]:
        """Get internal transactions for a parent transaction"""
        stmt = select(EvmInternalTransaction).filter_by(
            parent_tx=parent_tx_id,
        ).order_by(EvmInternalTransaction.trace_id)

        return list(self.session.execute(stmt).scalars().all())

    def add_address_mapping(
        self,
        tx_id: int,
        address: ChecksumEvmAddress,
    ) -> None:
        """Add an address mapping for a transaction"""
        mapping = EvmTxAddressMapping(
            tx_id=tx_id,
            address=address,
        )
        self.session.add(mapping)
        self.session.flush()

    def get_transactions_by_address(
        self,
        address: ChecksumEvmAddress,
        chain_id: int | None = None,
    ) -> list[EvmTransaction]:
        """Get all transactions involving an address"""
        query = (
            select(EvmTransaction)
            .join(EvmTxAddressMapping)
            .filter(EvmTxAddressMapping.address == address)
        )

        if chain_id is not None:
            query = query.filter(EvmTransaction.chain_id == chain_id)

        return list(self.session.execute(query).scalars().all())

    def is_transaction_decoded(self, tx_id: int) -> bool:
        """Check if a transaction is decoded"""
        stmt = select(EvmTxMapping).filter_by(
            tx_id=tx_id,
            value=1,  # 1 = decoded
        ).limit(1)
        return self.session.execute(stmt).scalar() is not None

    def mark_transaction_decoded(self, tx_id: int) -> None:
        """Mark a transaction as decoded"""
        if not self.is_transaction_decoded(tx_id):
            mapping = EvmTxMapping(tx_id=tx_id, value=1)
            self.session.add(mapping)
            self.session.flush()

    def delete_transaction(
        self,
        tx_hash: EVMTxHash,
        chain_id: int,
    ) -> bool:
        """Delete a transaction and all related data"""
        tx = self.get_transaction(tx_hash, chain_id)
        if tx:
            self.delete(tx)
            return True
        return False

    def get_transaction_count(
        self,
        address: ChecksumEvmAddress | None = None,
        chain_id: int | None = None,
    ) -> int:
        """Get count of transactions"""
        query = select(func.count()).select_from(EvmTransaction)

        if address:
            query = query.filter(
                or_(
                    EvmTransaction.from_address == address,
                    EvmTransaction.to_address == address,
                ),
            )

        if chain_id is not None:
            query = query.filter_by(chain_id=chain_id)

        return self.session.execute(query).scalar() or 0

    def add_optimism_data(
        self,
        tx_id: int,
        l1_fee: FVal,
    ) -> OptimismTransaction:
        """Add Optimism-specific transaction data"""
        opt_data = OptimismTransaction(
            tx_id=tx_id,
            l1_fee=str(l1_fee),
        )
        self.session.add(opt_data)
        self.session.flush()
        return opt_data
