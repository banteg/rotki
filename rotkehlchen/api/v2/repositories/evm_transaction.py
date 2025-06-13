"""Repository for managing EVM transactions."""
from typing import TYPE_CHECKING, Optional

from sqlmodel import func, select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.user.evm import (
    EvmTransaction,
    EvmTxReceipt,
)

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Timestamp


class EvmTransactionRepository(BaseRepository[EvmTransaction]):
    """Repository for managing EVM transactions."""

    model = EvmTransaction

    def get_transaction_by_hash(
        self,
        tx_hash: 'EVMTxHash',
        chain_id: int,
    ) -> EvmTransaction | None:
        """Get a transaction by its hash and chain."""
        query = select(self.model).where(
            self.model.tx_hash == tx_hash,
            self.model.chain_id == chain_id,
        )
        result = self.session.exec(query).first()
        return result

    def get_transactions_by_address(
        self,
        address: 'ChecksumEvmAddress',
        chain_id: int | None = None,
        from_timestamp: Optional['Timestamp'] = None,
        to_timestamp: Optional['Timestamp'] = None,
        limit: int | None = None,
    ) -> list[EvmTransaction]:
        """Get transactions involving a specific address."""
        query = select(self.model).where(
            (self.model.from_address == address) |
            (self.model.to_address == address),
        )

        if chain_id is not None:
            query = query.where(self.model.chain_id == chain_id)

        if from_timestamp is not None:
            query = query.where(self.model.timestamp >= from_timestamp)

        if to_timestamp is not None:
            query = query.where(self.model.timestamp <= to_timestamp)

        # Order by timestamp descending (most recent first)
        query = query.order_by(self.model.timestamp.desc())

        if limit is not None:
            query = query.limit(limit)

        result = self.session.exec(query)
        return list(result.all())

    def get_transactions_by_block(
        self,
        chain_id: int,
        block_number: int,
    ) -> list[EvmTransaction]:
        """Get all transactions in a specific block."""
        query = select(self.model).where(
            self.model.chain_id == chain_id,
            self.model.block_number == block_number,
        )
        result = self.session.exec(query)
        return list(result.all())

    def count_transactions_by_address(
        self,
        address: 'ChecksumEvmAddress',
        chain_id: int | None = None,
    ) -> dict[str, int]:
        """Count transactions sent and received by an address."""
        # Count sent transactions
        sent_query = select(func.count(self.model.identifier)).where(
            self.model.from_address == address,
        )

        # Count received transactions
        received_query = select(func.count(self.model.identifier)).where(
            self.model.to_address == address,
        )

        if chain_id is not None:
            sent_query = sent_query.where(self.model.chain_id == chain_id)
            received_query = received_query.where(self.model.chain_id == chain_id)

        sent_count = self.session.exec(sent_query).one()
        received_count = self.session.exec(received_query).one()

        return {
            'sent': sent_count,
            'received': received_count,
            'total': sent_count + received_count,
        }

    def get_pending_transactions(
        self,
        address: Optional['ChecksumEvmAddress'] = None,
    ) -> list[EvmTransaction]:
        """Get transactions that don't have receipts yet (pending)."""
        # Subquery to find transactions with receipts
        receipt_subquery = select(EvmTxReceipt.tx_id)

        # Main query for transactions without receipts
        query = select(self.model).where(
            ~self.model.identifier.in_(receipt_subquery),
        )

        if address:
            query = query.where(
                (self.model.from_address == address) |
                (self.model.to_address == address),
            )

        result = self.session.exec(query)
        return list(result.all())

    def get_failed_transactions(
        self,
        address: Optional['ChecksumEvmAddress'] = None,
        chain_id: int | None = None,
        from_timestamp: Optional['Timestamp'] = None,
    ) -> list[EvmTransaction]:
        """Get failed transactions."""
        # Join with receipts to check status
        query = (
            select(self.model)
            .join(EvmTxReceipt, EvmTxReceipt.tx_id == self.model.identifier)
            .where(EvmTxReceipt.status == 0)  # 0 = failed
        )

        if address:
            query = query.where(
                (self.model.from_address == address) |
                (self.model.to_address == address),
            )

        if chain_id is not None:
            query = query.where(self.model.chain_id == chain_id)

        if from_timestamp is not None:
            query = query.where(self.model.timestamp >= from_timestamp)

        result = self.session.exec(query)
        return list(result.all())

    def get_transaction_receipt(
        self,
        tx_hash: 'EVMTxHash',
        chain_id: int,
    ) -> EvmTxReceipt | None:
        """Get the receipt for a transaction."""
        # First get the transaction
        tx = self.get_transaction_by_hash(tx_hash, chain_id)
        if not tx:
            return None

        # Then get its receipt
        query = select(EvmTxReceipt).where(EvmTxReceipt.tx_id == tx.identifier)
        result = self.session.exec(query).first()
        return result

    def add_transaction_with_receipt(
        self,
        tx_data: dict,
        receipt_data: dict | None = None,
    ) -> EvmTransaction:
        """Add a transaction with its receipt."""
        # Create the transaction
        tx = self.create(tx_data)

        # Create the receipt if provided
        if receipt_data:
            receipt_data['tx_id'] = tx.identifier
            receipt = EvmTxReceipt(**receipt_data)
            self.session.add(receipt)
            self.session.commit()

        return tx

    def get_gas_stats_by_address(
        self,
        address: 'ChecksumEvmAddress',
        chain_id: int | None = None,
        from_timestamp: Optional['Timestamp'] = None,
    ) -> dict:
        """Get gas usage statistics for an address."""
        query = select(
            func.sum(self.model.gas_limit).label('total_gas_limit'),
            func.sum(self.model.gas_price).label('total_gas_price'),
            func.avg(self.model.gas_price).label('avg_gas_price'),
            func.count(self.model.identifier).label('tx_count'),
        ).where(self.model.from_address == address)

        if chain_id is not None:
            query = query.where(self.model.chain_id == chain_id)

        if from_timestamp is not None:
            query = query.where(self.model.timestamp >= from_timestamp)

        result = self.session.exec(query).one()

        return {
            'total_gas_limit': result.total_gas_limit or 0,
            'total_gas_price': result.total_gas_price or 0,
            'avg_gas_price': result.avg_gas_price or 0,
            'transaction_count': result.tx_count or 0,
        }
