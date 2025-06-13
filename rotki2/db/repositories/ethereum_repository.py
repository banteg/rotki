"""Repository for Ethereum chain data."""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_

from rotki2.common.types import ChecksumEvmAddress, EVMTxHash
from rotki2.db.models.user.ens import ENSMapping
from rotki2.db.models.user.eth2 import Eth2Deposit
from rotki2.db.models.user.evm import EvmTransaction, EvmTransactionReceipt

logger = logging.getLogger(__name__)


class EthereumRepository:
    """
    Repository for Ethereum-specific database operations.
    
    Handles all database interactions for Ethereum chain data including:
    - Transaction storage and retrieval
    - ENS name mappings
    - ETH2 deposit tracking
    - Chain-specific queries
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository with a database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
        self.chain_id = 1  # Ethereum mainnet chain ID
    
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
    
    async def save_receipt(self, receipt_data: dict[str, Any]) -> EvmTransactionReceipt:
        """
        Save a transaction receipt.
        
        Args:
            receipt_data: Receipt data from node
            
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
    
    # ENS-specific methods
    async def get_ens_mapping(self, address: ChecksumEvmAddress) -> ENSMapping | None:
        """
        Get ENS name for an address.
        
        Args:
            address: Ethereum address
            
        Returns:
            ENS mapping or None
        """
        stmt = select(ENSMapping).where(ENSMapping.address == address)
        result = await self.session.exec(stmt)
        return result.first()
    
    async def save_ens_mapping(
        self,
        address: ChecksumEvmAddress,
        ens_name: str,
        last_update: int | None = None,
    ) -> ENSMapping:
        """
        Save or update ENS mapping.
        
        Args:
            address: Ethereum address
            ens_name: ENS name
            last_update: Timestamp of last update
            
        Returns:
            Saved ENS mapping
        """
        # Check if mapping exists
        existing = await self.get_ens_mapping(address)
        
        if existing:
            existing.ens_name = ens_name
            if last_update:
                existing.last_update = last_update
            mapping = existing
        else:
            mapping = ENSMapping(
                address=address,
                ens_name=ens_name,
                last_update=last_update,
            )
            self.session.add(mapping)
        
        await self.session.commit()
        await self.session.refresh(mapping)
        
        return mapping
    
    async def get_ens_mappings_batch(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, str | None]:
        """
        Get ENS names for multiple addresses.
        
        Args:
            addresses: List of addresses
            
        Returns:
            Mapping of addresses to ENS names
        """
        stmt = select(ENSMapping).where(ENSMapping.address.in_(addresses))
        result = await self.session.exec(stmt)
        mappings = result.all()
        
        # Build result dict
        result_dict = {addr: None for addr in addresses}
        for mapping in mappings:
            result_dict[mapping.address] = mapping.ens_name
        
        return result_dict
    
    # ETH2-specific methods
    async def get_eth2_deposits(
        self,
        depositor: ChecksumEvmAddress | None = None,
        validator_index: int | None = None,
    ) -> list[Eth2Deposit]:
        """
        Get ETH2 deposits.
        
        Args:
            depositor: Filter by depositor address
            validator_index: Filter by validator index
            
        Returns:
            List of deposits
        """
        conditions = []
        
        if depositor:
            conditions.append(Eth2Deposit.from_address == depositor)
        
        if validator_index is not None:
            conditions.append(Eth2Deposit.validator_index == validator_index)
        
        if conditions:
            stmt = select(Eth2Deposit).where(and_(*conditions))
        else:
            stmt = select(Eth2Deposit)
        
        result = await self.session.exec(stmt)
        return result.all()
    
    async def save_eth2_deposit(
        self,
        tx_hash: EVMTxHash,
        from_address: ChecksumEvmAddress,
        pubkey: str,
        withdrawal_credentials: str,
        amount: str,
        signature: str,
        deposit_index: int,
        block_number: int,
        timestamp: int,
        validator_index: int | None = None,
    ) -> Eth2Deposit:
        """
        Save an ETH2 deposit.
        
        Args:
            tx_hash: Transaction hash of the deposit
            from_address: Address that made the deposit
            pubkey: Validator public key
            withdrawal_credentials: Withdrawal credentials
            amount: Amount deposited in wei
            signature: Deposit signature
            deposit_index: Deposit index in the contract
            block_number: Block number of deposit
            timestamp: Timestamp of deposit
            validator_index: Validator index (if known)
            
        Returns:
            Saved deposit
        """
        deposit = Eth2Deposit(
            tx_hash=tx_hash,
            from_address=from_address,
            pubkey=pubkey,
            withdrawal_credentials=withdrawal_credentials,
            amount=amount,
            signature=signature,
            deposit_index=deposit_index,
            block_number=block_number,
            timestamp=timestamp,
            validator_index=validator_index,
        )
        
        self.session.add(deposit)
        await self.session.commit()
        await self.session.refresh(deposit)
        
        return deposit
    
    async def has_eth2_deposit(self, tx_hash: EVMTxHash) -> bool:
        """
        Check if an ETH2 deposit exists.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            True if deposit exists
        """
        stmt = select(Eth2Deposit.tx_hash).where(Eth2Deposit.tx_hash == tx_hash)
        result = await self.session.exec(stmt)
        return result.first() is not None
    
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