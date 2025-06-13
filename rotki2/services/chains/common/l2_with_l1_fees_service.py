"""Base service for L2 chains with L1 fee structures."""
import logging
from abc import ABC
from decimal import Decimal
from typing import Any

from rotki2.common.types import ChecksumEvmAddress, EVMTxHash
from rotki2.services.chains.common.evm_service import BaseEvmService

logger = logging.getLogger(__name__)


class L2WithL1FeesService(BaseEvmService, ABC):
    """
    Base service for L2 chains that have additional L1 fee components.
    
    This includes chains like Optimism, Arbitrum, Base, and Scroll which
    charge L1 fees for data availability in addition to L2 execution costs.
    """
    
    async def get_transaction_receipt(self, tx_hash: EVMTxHash) -> dict[str, Any] | None:
        """
        Get transaction receipt with L1 fee information.
        
        L2 receipts may include additional fields like l1Fee.
        """
        receipt = await super().get_transaction_receipt(tx_hash)
        
        if receipt and "l1Fee" in receipt:
            # Ensure L1 fee is properly formatted
            try:
                l1_fee = receipt.get("l1Fee")
                if isinstance(l1_fee, str) and l1_fee.startswith("0x"):
                    receipt["l1Fee"] = str(int(l1_fee, 16))
            except Exception as e:
                logger.warning(f"Failed to parse L1 fee for {tx_hash}: {e}")
        
        return receipt
    
    async def get_total_transaction_cost(
        self,
        tx_hash: EVMTxHash,
    ) -> dict[str, str]:
        """
        Calculate total transaction cost including L1 fees.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Dictionary with l2_cost, l1_cost, and total_cost in wei
        """
        receipt = await self.get_transaction_receipt(tx_hash)
        if not receipt:
            raise ValueError(f"Receipt not found for {tx_hash}")
        
        tx = await self.get_transaction(tx_hash)
        if not tx:
            raise ValueError(f"Transaction not found for {tx_hash}")
        
        # Calculate L2 cost (gas_used * gas_price)
        gas_used = Decimal(receipt.get("gasUsed", "0"))
        gas_price = Decimal(tx.gas_price) if hasattr(tx, "gas_price") and tx.gas_price else Decimal(0)
        l2_cost = gas_used * gas_price
        
        # Get L1 cost from receipt
        l1_cost = Decimal(receipt.get("l1Fee", 0))
        
        # Total cost
        total_cost = l2_cost + l1_cost
        
        return {
            "l2_cost": str(l2_cost),
            "l1_cost": str(l1_cost),
            "total_cost": str(total_cost),
        }
    
    async def estimate_l1_fee(
        self,
        data: bytes,
        gas_price: int | None = None,
    ) -> int:
        """
        Estimate L1 fee for a transaction.
        
        This is chain-specific and should be overridden by subclasses.
        
        Args:
            data: Transaction data
            gas_price: L1 gas price (if known)
            
        Returns:
            Estimated L1 fee in wei
        """
        # Default implementation - subclasses should override
        logger.warning(f"L1 fee estimation not implemented for {self.chain_name}")
        return 0