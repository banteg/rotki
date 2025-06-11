"""Repository for ETH2 staking details management"""

from typing import Optional

from sqlalchemy import select

from rotkehlchen.db.orm.models import ETH2StakingDetail
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Timestamp


class ETH2StakingRepository(BaseRepository[ETH2StakingDetail]):
    """Repository for managing ETH2 staking details"""
    
    def __init__(self, session):
        super().__init__(session, ETH2StakingDetail)
    
    def add_staking_detail(
        self,
        eth1_depositor: ChecksumEvmAddress,
        tx_hash: str,
        tx_index: int,
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress,
        timestamp: Timestamp,
        deposited_amount: FVal,
        withdrawal_credentials: str,
        amount: FVal,
        usd_value: FVal,
    ) -> ETH2StakingDetail:
        """Add ETH2 staking details"""
        detail = ETH2StakingDetail(
            eth1_depositor=eth1_depositor,
            tx_hash=tx_hash,
            tx_index=tx_index,
            from_address=from_address,
            to_address=to_address,
            timestamp=int(timestamp),
            deposited_amount=str(deposited_amount),
            withdrawal_credentials=withdrawal_credentials,
            amount=str(amount),
            usd_value=str(usd_value),
        )
        return self.add(detail)
    
    def get_staking_details(
        self,
        eth1_depositor: Optional[ChecksumEvmAddress] = None,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[ETH2StakingDetail]:
        """Get staking details with filters"""
        query = select(ETH2StakingDetail)
        
        if eth1_depositor:
            query = query.filter_by(eth1_depositor=eth1_depositor)
        
        if from_timestamp is not None:
            query = query.filter(ETH2StakingDetail.timestamp >= int(from_timestamp))
        
        if to_timestamp is not None:
            query = query.filter(ETH2StakingDetail.timestamp <= int(to_timestamp))
        
        # Order by timestamp descending
        query = query.order_by(ETH2StakingDetail.timestamp.desc())
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        
        return list(self.session.execute(query).scalars().all())
    
    def get_staking_detail_by_tx(
        self,
        tx_hash: str,
        tx_index: int,
    ) -> Optional[ETH2StakingDetail]:
        """Get staking detail by transaction hash and index"""
        return self.get(tx_hash=tx_hash, tx_index=tx_index)
    
    def delete_staking_detail(
        self,
        tx_hash: str,
        tx_index: int,
    ) -> bool:
        """Delete a staking detail"""
        return self.delete_by(tx_hash=tx_hash, tx_index=tx_index) > 0
    
    def get_total_deposited(
        self,
        eth1_depositor: Optional[ChecksumEvmAddress] = None,
    ) -> FVal:
        """Get total amount deposited"""
        query = select(func.sum(ETH2StakingDetail.deposited_amount))
        
        if eth1_depositor:
            query = query.filter_by(eth1_depositor=eth1_depositor)
        
        result = self.session.execute(query).scalar()
        return FVal(result) if result else FVal(0)
    
    def get_deposits_count(
        self,
        eth1_depositor: Optional[ChecksumEvmAddress] = None,
    ) -> int:
        """Get count of deposits"""
        query = select(func.count()).select_from(ETH2StakingDetail)
        
        if eth1_depositor:
            query = query.filter_by(eth1_depositor=eth1_depositor)
        
        return self.session.execute(query).scalar() or 0
    
    def get_depositors(self) -> list[ChecksumEvmAddress]:
        """Get unique list of depositors"""
        stmt = select(ETH2StakingDetail.eth1_depositor).distinct()
        return list(self.session.execute(stmt).scalars().all())
    
    def update_usd_value(
        self,
        tx_hash: str,
        tx_index: int,
        usd_value: FVal,
    ) -> Optional[ETH2StakingDetail]:
        """Update USD value for a staking detail"""
        detail = self.get_staking_detail_by_tx(tx_hash, tx_index)
        if not detail:
            return None
        
        detail.usd_value = str(usd_value)
        return self.update(detail)
    
    def get_deposits_by_address(
        self,
        address: ChecksumEvmAddress,
    ) -> list[ETH2StakingDetail]:
        """Get all deposits where address is depositor, from or to"""
        stmt = select(ETH2StakingDetail).filter(
            or_(
                ETH2StakingDetail.eth1_depositor == address,
                ETH2StakingDetail.from_address == address,
                ETH2StakingDetail.to_address == address,
            )
        ).order_by(ETH2StakingDetail.timestamp.desc())
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_deposits_in_range(
        self,
        start_timestamp: Timestamp,
        end_timestamp: Timestamp,
    ) -> list[ETH2StakingDetail]:
        """Get deposits within timestamp range"""
        stmt = select(ETH2StakingDetail).filter(
            ETH2StakingDetail.timestamp.between(
                int(start_timestamp),
                int(end_timestamp),
            )
        ).order_by(ETH2StakingDetail.timestamp)
        
        return list(self.session.execute(stmt).scalars().all())