"""Repository for Gnosis Pay transactions."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col, func

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.defi import GnosisPayData

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class GnosisPayRepository(AsyncBaseRepository[GnosisPayData]):
    """Repository for handling Gnosis Pay data."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, GnosisPayData)

    async def get_by_tx_hash(self, tx_hash: bytes) -> GnosisPayData | None:
        """Get Gnosis Pay data by transaction hash.
        
        Args:
            tx_hash: The transaction hash
            
        Returns:
            GnosisPayData if found, None otherwise
        """
        result = await self.session.exec(
            select(GnosisPayData).where(
                col(GnosisPayData.tx_hash) == tx_hash
            )
        )
        return result.first()

    async def get_by_merchant(self, merchant_name: str) -> list[GnosisPayData]:
        """Get all transactions for a specific merchant.
        
        Args:
            merchant_name: The merchant name
            
        Returns:
            List of Gnosis Pay transactions
        """
        result = await self.session.exec(
            select(GnosisPayData).where(
                col(GnosisPayData.merchant_name) == merchant_name
            ).order_by(GnosisPayData.timestamp.desc())
        )
        return list(result.all())

    async def get_by_country(self, country: str) -> list[GnosisPayData]:
        """Get all transactions for a specific country.
        
        Args:
            country: The country code
            
        Returns:
            List of Gnosis Pay transactions
        """
        result = await self.session.exec(
            select(GnosisPayData).where(
                col(GnosisPayData.country) == country
            ).order_by(GnosisPayData.timestamp.desc())
        )
        return list(result.all())

    async def get_transactions_in_range(
        self,
        start_timestamp: int,
        end_timestamp: int,
        merchant_name: str | None = None,
        country: str | None = None,
    ) -> list[GnosisPayData]:
        """Get Gnosis Pay transactions within a timestamp range.
        
        Args:
            start_timestamp: Start of the time range
            end_timestamp: End of the time range
            merchant_name: Optional merchant filter
            country: Optional country filter
            
        Returns:
            List of Gnosis Pay transactions
        """
        query = select(GnosisPayData).where(
            col(GnosisPayData.timestamp) >= start_timestamp,
            col(GnosisPayData.timestamp) <= end_timestamp,
        )
        
        if merchant_name:
            query = query.where(col(GnosisPayData.merchant_name) == merchant_name)
        if country:
            query = query.where(col(GnosisPayData.country) == country)
            
        query = query.order_by(GnosisPayData.timestamp)
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_spending_by_merchant(
        self,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[dict[str, str]]:
        """Get total spending grouped by merchant.
        
        Args:
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of dicts with merchant_name, transaction_count, and total_amount
        """
        query = select(
            GnosisPayData.merchant_name,
            func.count(GnosisPayData.identifier).label('transaction_count'),
            func.sum(GnosisPayData.transaction_amount).label('total_amount'),
        ).group_by(GnosisPayData.merchant_name)
        
        if start_timestamp:
            query = query.where(col(GnosisPayData.timestamp) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(GnosisPayData.timestamp) <= end_timestamp)
        
        result = await self.session.exec(query)
        
        return [
            {
                'merchant_name': row[0],
                'transaction_count': str(row[1]),
                'total_amount': str(row[2] or 0),
            }
            for row in result.all()
        ]

    async def get_spending_by_category(
        self,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[dict[str, str]]:
        """Get total spending grouped by MCC (Merchant Category Code).
        
        Args:
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of dicts with mcc, transaction_count, and total_amount
        """
        query = select(
            GnosisPayData.mcc,
            func.count(GnosisPayData.identifier).label('transaction_count'),
            func.sum(GnosisPayData.transaction_amount).label('total_amount'),
        ).group_by(GnosisPayData.mcc)
        
        if start_timestamp:
            query = query.where(col(GnosisPayData.timestamp) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(GnosisPayData.timestamp) <= end_timestamp)
        
        result = await self.session.exec(query)
        
        return [
            {
                'mcc': str(row[0]),
                'transaction_count': str(row[1]),
                'total_amount': str(row[2] or 0),
            }
            for row in result.all()
        ]

    async def get_reversals(self) -> list[GnosisPayData]:
        """Get all transactions that have been reversed.
        
        Returns:
            List of reversed transactions
        """
        result = await self.session.exec(
            select(GnosisPayData).where(
                col(GnosisPayData.reversal_tx_hash).is_not(None)
            ).order_by(GnosisPayData.timestamp.desc())
        )
        return list(result.all())