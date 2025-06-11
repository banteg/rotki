"""Repository for Gnosis Pay management"""


from sqlalchemy import func, select

from rotkehlchen.db.orm.protocols import GnosisPayData
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp


class GnosisPayRepository(BaseRepository[GnosisPayData]):
    """Repository for managing Gnosis Pay data"""

    def __init__(self, session):
        super().__init__(session, GnosisPayData)

    def add_payment(
        self,
        tx_hash: bytes,
        timestamp: Timestamp,
        merchant_name: str,
        country: str,
        mcc: int,
        transaction_symbol: str,
        transaction_amount: FVal,
        merchant_city: str | None = None,
        billing_symbol: str | None = None,
        billing_amount: FVal | None = None,
        reversal_symbol: str | None = None,
        reversal_amount: FVal | None = None,
        reversal_tx_hash: bytes | None = None,
    ) -> GnosisPayData:
        """Add a Gnosis Pay payment record"""
        payment = GnosisPayData(
            tx_hash=tx_hash,
            timestamp=int(timestamp),
            merchant_name=merchant_name,
            merchant_city=merchant_city,
            country=country,
            mcc=mcc,
            transaction_symbol=transaction_symbol,
            transaction_amount=str(transaction_amount),
            billing_symbol=billing_symbol,
            billing_amount=str(billing_amount) if billing_amount else None,
            reversal_symbol=reversal_symbol,
            reversal_amount=str(reversal_amount) if reversal_amount else None,
            reversal_tx_hash=reversal_tx_hash,
        )
        return self.add(payment)

    def get_payment(self, identifier: int) -> GnosisPayData | None:
        """Get a payment by identifier"""
        return self.get(identifier=identifier)

    def get_payment_by_tx_hash(self, tx_hash: bytes) -> GnosisPayData | None:
        """Get payment by transaction hash"""
        return self.get(tx_hash=tx_hash)

    def get_payments(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
        merchant_name: str | None = None,
        country: str | None = None,
        transaction_symbol: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[GnosisPayData]:
        """Get payments with filters"""
        query = select(GnosisPayData)

        if from_timestamp is not None:
            query = query.filter(GnosisPayData.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(GnosisPayData.timestamp <= int(to_timestamp))

        if merchant_name:
            query = query.filter_by(merchant_name=merchant_name)

        if country:
            query = query.filter_by(country=country)

        if transaction_symbol:
            query = query.filter_by(transaction_symbol=transaction_symbol)

        # Order by timestamp descending
        query = query.order_by(GnosisPayData.timestamp.desc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def delete_payment(self, identifier: int) -> bool:
        """Delete a payment"""
        return self.delete_by(identifier=identifier) > 0

    def payment_exists(self, tx_hash: bytes) -> bool:
        """Check if a payment exists"""
        return self.get_payment_by_tx_hash(tx_hash) is not None

    def get_payments_by_merchant(
        self,
        merchant_name: str,
    ) -> list[GnosisPayData]:
        """Get all payments for a specific merchant"""
        stmt = select(GnosisPayData).filter_by(
            merchant_name=merchant_name,
        ).order_by(GnosisPayData.timestamp.desc())

        return list(self.session.execute(stmt).scalars().all())

    def get_total_spent(
        self,
        transaction_symbol: str | None = None,
        merchant_name: str | None = None,
        country: str | None = None,
    ) -> FVal:
        """Get total amount spent"""
        query = select(func.sum(GnosisPayData.transaction_amount))

        if transaction_symbol:
            query = query.filter_by(transaction_symbol=transaction_symbol)
        if merchant_name:
            query = query.filter_by(merchant_name=merchant_name)
        if country:
            query = query.filter_by(country=country)

        result = self.session.execute(query).scalar()
        return FVal(result) if result else FVal(0)

    def get_payments_count(
        self,
        merchant_name: str | None = None,
        country: str | None = None,
    ) -> int:
        """Get count of payments"""
        query = select(func.count()).select_from(GnosisPayData)

        if merchant_name:
            query = query.filter_by(merchant_name=merchant_name)
        if country:
            query = query.filter_by(country=country)

        return self.session.execute(query).scalar() or 0

    def get_unique_merchants(self) -> list[str]:
        """Get list of unique merchants"""
        stmt = select(GnosisPayData.merchant_name).distinct()
        return list(self.session.execute(stmt).scalars().all())

    def get_unique_countries(self) -> list[str]:
        """Get list of unique countries"""
        stmt = select(GnosisPayData.country).distinct()
        return list(self.session.execute(stmt).scalars().all())

    def get_spending_summary_by_symbol(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
    ) -> dict[str, FVal]:
        """Get spending summary by transaction symbol"""
        query = select(
            GnosisPayData.transaction_symbol,
            func.sum(GnosisPayData.transaction_amount).label('total'),
        ).group_by(GnosisPayData.transaction_symbol)

        if from_timestamp is not None:
            query = query.filter(GnosisPayData.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(GnosisPayData.timestamp <= int(to_timestamp))

        results = self.session.execute(query).all()
        return {row.transaction_symbol: FVal(row.total) for row in results}

    def get_latest_payment(
        self,
        merchant_name: str | None = None,
    ) -> GnosisPayData | None:
        """Get the most recent payment"""
        query = select(GnosisPayData)

        if merchant_name:
            query = query.filter_by(merchant_name=merchant_name)

        query = query.order_by(GnosisPayData.timestamp.desc()).limit(1)

        return self.session.execute(query).scalar_one_or_none()

    def get_reversals(self) -> list[GnosisPayData]:
        """Get all payments that have been reversed"""
        stmt = select(GnosisPayData).filter(
            GnosisPayData.reversal_tx_hash.isnot(None),
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_payments_by_mcc(self, mcc: int) -> list[GnosisPayData]:
        """Get all payments for a specific merchant category code"""
        return self.get_all(mcc=mcc)