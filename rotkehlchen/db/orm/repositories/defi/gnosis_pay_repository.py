"""Repository for Gnosis Pay management"""

from typing import Optional

from sqlalchemy import select

from rotkehlchen.db.orm.models import GnosisPay
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Timestamp


class GnosisPayRepository(BaseRepository[GnosisPay]):
    """Repository for managing Gnosis Pay data"""
    
    def __init__(self, session):
        super().__init__(session, GnosisPay)
    
    def add_payment(
        self,
        tx_hash: str,
        timestamp: Timestamp,
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress,
        token: str,
        amount: FVal,
        card_address: Optional[ChecksumEvmAddress] = None,
    ) -> GnosisPay:
        """Add a Gnosis Pay payment record"""
        payment = GnosisPay(
            tx_hash=tx_hash,
            timestamp=int(timestamp),
            from_address=from_address,
            to_address=to_address,
            token=token,
            amount=str(amount),
            card_address=card_address,
        )
        return self.add(payment)
    
    def get_payment(self, identifier: int) -> Optional[GnosisPay]:
        """Get a payment by identifier"""
        return self.get(identifier=identifier)
    
    def get_payment_by_tx_hash(self, tx_hash: str) -> Optional[GnosisPay]:
        """Get payment by transaction hash"""
        return self.get(tx_hash=tx_hash)
    
    def get_payments(
        self,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
        from_address: Optional[ChecksumEvmAddress] = None,
        to_address: Optional[ChecksumEvmAddress] = None,
        card_address: Optional[ChecksumEvmAddress] = None,
        token: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[GnosisPay]:
        """Get payments with filters"""
        query = select(GnosisPay)
        
        if from_timestamp is not None:
            query = query.filter(GnosisPay.timestamp >= int(from_timestamp))
        
        if to_timestamp is not None:
            query = query.filter(GnosisPay.timestamp <= int(to_timestamp))
        
        if from_address:
            query = query.filter_by(from_address=from_address)
        
        if to_address:
            query = query.filter_by(to_address=to_address)
        
        if card_address:
            query = query.filter_by(card_address=card_address)
        
        if token:
            query = query.filter_by(token=token)
        
        # Order by timestamp descending
        query = query.order_by(GnosisPay.timestamp.desc())
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        
        return list(self.session.execute(query).scalars().all())
    
    def delete_payment(self, identifier: int) -> bool:
        """Delete a payment"""
        return self.delete_by(identifier=identifier) > 0
    
    def payment_exists(self, tx_hash: str) -> bool:
        """Check if a payment exists"""
        return self.get_payment_by_tx_hash(tx_hash) is not None
    
    def get_payments_by_card(
        self,
        card_address: ChecksumEvmAddress,
    ) -> list[GnosisPay]:
        """Get all payments for a specific card"""
        stmt = select(GnosisPay).filter_by(
            card_address=card_address
        ).order_by(GnosisPay.timestamp.desc())
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_total_spent(
        self,
        from_address: Optional[ChecksumEvmAddress] = None,
        card_address: Optional[ChecksumEvmAddress] = None,
        token: Optional[str] = None,
    ) -> FVal:
        """Get total amount spent"""
        query = select(func.sum(GnosisPay.amount))
        
        if from_address:
            query = query.filter_by(from_address=from_address)
        if card_address:
            query = query.filter_by(card_address=card_address)
        if token:
            query = query.filter_by(token=token)
        
        result = self.session.execute(query).scalar()
        return FVal(result) if result else FVal(0)
    
    def get_payments_count(
        self,
        from_address: Optional[ChecksumEvmAddress] = None,
        card_address: Optional[ChecksumEvmAddress] = None,
    ) -> int:
        """Get count of payments"""
        query = select(func.count()).select_from(GnosisPay)
        
        if from_address:
            query = query.filter_by(from_address=from_address)
        if card_address:
            query = query.filter_by(card_address=card_address)
        
        return self.session.execute(query).scalar() or 0
    
    def get_unique_cards(self) -> list[ChecksumEvmAddress]:
        """Get list of unique card addresses"""
        stmt = select(GnosisPay.card_address).distinct().filter(
            GnosisPay.card_address.isnot(None)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_unique_tokens(self) -> list[str]:
        """Get list of unique tokens used"""
        stmt = select(GnosisPay.token).distinct()
        return list(self.session.execute(stmt).scalars().all())
    
    def get_spending_summary(
        self,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
    ) -> dict[str, FVal]:
        """Get spending summary by token"""
        query = select(
            GnosisPay.token,
            func.sum(GnosisPay.amount).label('total')
        ).group_by(GnosisPay.token)
        
        if from_timestamp is not None:
            query = query.filter(GnosisPay.timestamp >= int(from_timestamp))
        
        if to_timestamp is not None:
            query = query.filter(GnosisPay.timestamp <= int(to_timestamp))
        
        results = self.session.execute(query).all()
        return {row.token: FVal(row.total) for row in results}
    
    def get_latest_payment(
        self,
        card_address: Optional[ChecksumEvmAddress] = None,
    ) -> Optional[GnosisPay]:
        """Get the most recent payment"""
        query = select(GnosisPay)
        
        if card_address:
            query = query.filter_by(card_address=card_address)
        
        query = query.order_by(GnosisPay.timestamp.desc()).limit(1)
        
        return self.session.execute(query).scalar_one_or_none()