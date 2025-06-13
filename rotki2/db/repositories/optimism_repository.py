"""Repository for Optimism chain data."""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_

from rotki2.common.types import ChecksumEvmAddress, EVMTxHash
from rotki2.db.models.user.evm import EvmTransaction, EvmTransactionReceipt

logger = logging.getLogger(__name__)


class OptimismRepository:
    """
    Repository for Optimism-specific database operations.
    
    Handles all database interactions for Optimism chain data including:
    - Transaction storage and retrieval
    - Receipt management with L1 fee data
    - Address tracking
    - Chain-specific queries
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository with a database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
        self.chain_id = 10  # Optimism chain ID
    
    async def get_transaction(self, tx_hash: EVMTxHash) -> EvmTransaction | None:
        """
        Get a transaction by hash.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction or None if not found
        """
        stmt = select(EvmTransaction).where(
            and_(
                EvmTransaction.tx_hash == tx_hash,
                EvmTransaction.chain_id == self.chain_id,
            )
        )
        
        result = await self.session.exec(stmt)
        return result.first()
    
    async def save_transaction(self, tx_data: dict[str, Any]) -> EvmTransaction:
        """
        Save a transaction to the database.
        
        Args:
            tx_data: Transaction data from node
            
        Returns:
            Saved transaction model
        """
        transaction = EvmTransaction(
            tx_hash=tx_data["hash"],
            chain_id=self.chain_id,
            timestamp=tx_data.get("timestamp"),
            block_number=int(tx_data["blockNumber"], 16),
            from_address=tx_data["from"],
            to_address=tx_data.get("to"),
            value=str(int(tx_data["value"], 16)),
            gas=str(int(tx_data["gas"], 16)),
            gas_price=str(int(tx_data.get("gasPrice", "0"), 16)),
            gas_used=None,  # Will be set from receipt
            input_data=tx_data["input"],
            nonce=int(tx_data["nonce"], 16),
        )
        
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        
        return transaction
    
    async def get_receipt(self, tx_hash: EVMTxHash) -> EvmTransactionReceipt | None:
        """
        Get a transaction receipt by hash.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Receipt or None if not found
        """
        stmt = select(EvmTransactionReceipt).where(
            and_(
                EvmTransactionReceipt.tx_hash == tx_hash,
                EvmTransactionReceipt.chain_id == self.chain_id,
            )
        )
        
        result = await self.session.exec(stmt)
        return result.first()
    
    async def save_receipt(
        self,
        receipt_data: dict[str, Any],
        l1_fee: str | None = None,
    ) -> EvmTransactionReceipt:
        """
        Save a transaction receipt with Optimism-specific data.
        
        Args:
            receipt_data: Receipt data from node
            l1_fee: L1 fee in wei (Optimism-specific)
            
        Returns:
            Saved receipt model
        """
        receipt = EvmTransactionReceipt(
            tx_hash=receipt_data["transactionHash"],
            chain_id=self.chain_id,
            contract_address=receipt_data.get("contractAddress"),
            cumulative_gas_used=str(int(receipt_data["cumulativeGasUsed"], 16)),
            gas_used=str(int(receipt_data["gasUsed"], 16)),
            logs=receipt_data.get("logs", []),
            status=int(receipt_data["status"], 16) == 1,
            # Store L1 fee in extra_data for Optimism
            extra_data={"l1_fee": l1_fee} if l1_fee else None,
        )
        
        self.session.add(receipt)
        
        # Update transaction gas_used if we have it
        if receipt.gas_used:
            stmt = select(EvmTransaction).where(
                and_(
                    EvmTransaction.tx_hash == receipt.tx_hash,
                    EvmTransaction.chain_id == self.chain_id,
                )
            )
            result = await self.session.exec(stmt)
            tx = result.first()
            if tx:
                tx.gas_used = receipt.gas_used
        
        await self.session.commit()
        await self.session.refresh(receipt)
        
        return receipt
    
    async def get_transactions_for_address(
        self,
        address: ChecksumEvmAddress,
        from_block: int | None = None,
        to_block: int | None = None,
        limit: int = 100,
    ) -> list[EvmTransaction]:
        """
        Get transactions for an address.
        
        Args:
            address: Address to query
            from_block: Starting block number (optional)
            to_block: Ending block number (optional)
            limit: Maximum number of results
            
        Returns:
            List of transactions
        """
        conditions = [
            EvmTransaction.chain_id == self.chain_id,
            (EvmTransaction.from_address == address) | (EvmTransaction.to_address == address),
        ]
        
        if from_block is not None:
            conditions.append(EvmTransaction.block_number >= from_block)
        
        if to_block is not None:
            conditions.append(EvmTransaction.block_number <= to_block)
        
        stmt = (
            select(EvmTransaction)
            .where(and_(*conditions))
            .order_by(EvmTransaction.block_number.desc())
            .limit(limit)
        )
        
        result = await self.session.exec(stmt)
        return result.all()
    
    async def get_latest_block_number(self) -> int | None:
        """
        Get the latest block number we have data for.
        
        Returns:
            Latest block number or None if no data
        """
        stmt = (
            select(EvmTransaction.block_number)
            .where(EvmTransaction.chain_id == self.chain_id)
            .order_by(EvmTransaction.block_number.desc())
            .limit(1)
        )
        
        result = await self.session.exec(stmt)
        return result.first()
    
    async def has_transaction(self, tx_hash: EVMTxHash) -> bool:
        """
        Check if a transaction exists in the database.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            True if transaction exists
        """
        stmt = select(EvmTransaction.tx_hash).where(
            and_(
                EvmTransaction.tx_hash == tx_hash,
                EvmTransaction.chain_id == self.chain_id,
            )
        )
        
        result = await self.session.exec(stmt)
        return result.first() is not None
    
    async def delete_transactions_after_block(self, block_number: int) -> int:
        """
        Delete transactions after a certain block (for reorg handling).
        
        Args:
            block_number: Block number to delete after
            
        Returns:
            Number of deleted transactions
        """
        # First get transactions to delete
        stmt = select(EvmTransaction).where(
            and_(
                EvmTransaction.chain_id == self.chain_id,
                EvmTransaction.block_number > block_number,
            )
        )
        
        result = await self.session.exec(stmt)
        transactions = result.all()
        
        count = len(transactions)
        
        # Delete transactions and their receipts
        for tx in transactions:
            # Delete receipt first
            receipt_stmt = select(EvmTransactionReceipt).where(
                and_(
                    EvmTransactionReceipt.tx_hash == tx.tx_hash,
                    EvmTransactionReceipt.chain_id == self.chain_id,
                )
            )
            receipt_result = await self.session.exec(receipt_stmt)
            receipt = receipt_result.first()
            if receipt:
                await self.session.delete(receipt)
            
            # Then delete transaction
            await self.session.delete(tx)
        
        await self.session.commit()
        
        logger.info(f"Deleted {count} Optimism transactions after block {block_number}")
        return count