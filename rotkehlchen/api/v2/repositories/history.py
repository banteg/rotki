"""History repository for v2 API.

Handles all database operations related to transaction history.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.user.history import EvmEventInfo, HistoryEvent


class HistoryRepository(BaseRepository[HistoryEvent]):
    """Repository for history-related database operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, HistoryEvent)
    
    def find_by_event_identifier(self, event_identifier: str) -> list[HistoryEvent]:
        """Find events by event identifier."""
        statement = select(HistoryEvent).where(HistoryEvent.event_identifier == event_identifier)
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_tx_hash(self, tx_hash: bytes) -> list[HistoryEvent]:
        """Find events by transaction hash (for EVM events)."""
        # Join with evm_events_info to filter by tx_hash
        statement = (
            select(HistoryEvent)
            .join(EvmEventInfo)
            .where(EvmEventInfo.tx_hash == tx_hash)
        )
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_address(self, address: str) -> list[HistoryEvent]:
        """Find all events for an address."""
        # Join with evm_events_info to filter by address
        statement = (
            select(HistoryEvent)
            .join(EvmEventInfo, isouter=True)
            .where(
                (HistoryEvent.location_label == address) |
                (EvmEventInfo.address == address)
            )
        )
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_timestamp_range(
        self,
        start: datetime,
        end: datetime,
        address: Optional[str] = None,
    ) -> list[HistoryEvent]:
        """Find events within a timestamp range."""
        # Convert datetime to timestamp if needed
        start_ts = int(start.timestamp()) if isinstance(start, datetime) else start
        end_ts = int(end.timestamp()) if isinstance(end, datetime) else end
        
        statement = select(HistoryEvent).where(
            (HistoryEvent.timestamp >= start_ts) &
            (HistoryEvent.timestamp <= end_ts)
        )
        
        if address:
            statement = (
                statement.join(EvmEventInfo, isouter=True)
                .where(
                    (HistoryEvent.location_label == address) |
                    (EvmEventInfo.address == address)
                )
            )
        
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_type(self, event_type: str, subtype: Optional[str] = None) -> list[HistoryEvent]:
        """Find all events of a specific type."""
        statement = select(HistoryEvent).where(HistoryEvent.type == event_type)
        if subtype:
            statement = statement.where(HistoryEvent.subtype == subtype)
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by(self, **kwargs) -> list[HistoryEvent]:
        """Find events by multiple criteria."""
        statement = select(HistoryEvent)
        
        for key, value in kwargs.items():
            if hasattr(HistoryEvent, key):
                statement = statement.where(getattr(HistoryEvent, key) == value)
        
        results = self.session.exec(statement)
        return list(results.all())
    
    def get_latest_events(self, limit: int = 100) -> list[HistoryEvent]:
        """Get the latest events."""
        statement = select(HistoryEvent).order_by(
            HistoryEvent.timestamp.desc()
        ).limit(limit)
        results = self.session.exec(statement)
        return list(results.all())
    
    def exists_by_event_identifier(self, event_identifier: str) -> bool:
        """Check if event exists by event identifier."""
        return len(self.find_by_event_identifier(event_identifier)) > 0
    
    def get_ignored_events(self) -> list[HistoryEvent]:
        """Get all ignored events."""
        statement = select(HistoryEvent).where(HistoryEvent.ignored == 1)
        results = self.session.exec(statement)
        return list(results.all())