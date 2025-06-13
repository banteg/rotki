"""History repository for v2 API.

Handles all database operations related to transaction history.
"""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, cast, func, or_, text
from sqlalchemy.sql import Select
from sqlmodel import Session, select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.db.models.user.history import (
    EvmEventInfo,
    HistoryEvent,
    HistoryEventMapping,
)
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.types import Location, Timestamp


class HistoryEventFilter:
    """Filter criteria for history events queries."""
    
    def __init__(
        self,
        event_identifiers: list[str] | None = None,
        from_ts: Timestamp | None = None,
        to_ts: Timestamp | None = None,
        location: Location | None = None,
        locations: list[Location] | None = None,
        asset: str | None = None,
        assets: list[str] | None = None,
        event_types: list[str] | None = None,
        event_subtypes: list[str] | None = None,
        entry_types: list[HistoryBaseEntryType] | None = None,
        tx_hashes: list[bytes] | None = None,
        addresses: list[str] | None = None,
        counterparties: list[str] | None = None,
        products: list[str] | None = None,
        exclude_ignored: bool = False,
        group_by_event_ids: bool = False,
    ):
        self.event_identifiers = event_identifiers
        self.from_ts = from_ts
        self.to_ts = to_ts
        self.location = location
        self.locations = locations
        self.asset = asset
        self.assets = assets
        self.event_types = event_types
        self.event_subtypes = event_subtypes
        self.entry_types = entry_types
        self.tx_hashes = tx_hashes
        self.addresses = addresses
        self.counterparties = counterparties
        self.products = products
        self.exclude_ignored = exclude_ignored
        self.group_by_event_ids = group_by_event_ids


class HistoryRepository(BaseRepository[HistoryEvent]):
    """Repository for history-related database operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, HistoryEvent)
    
    def _apply_filters(
        self,
        statement: Select[tuple[HistoryEvent]],
        filters: HistoryEventFilter,
    ) -> Select[tuple[HistoryEvent]]:
        """Apply filters to a history events query."""
        # Basic filters
        if filters.event_identifiers:
            statement = statement.where(HistoryEvent.event_identifier.in_(filters.event_identifiers))
        
        if filters.from_ts:
            statement = statement.where(HistoryEvent.timestamp >= filters.from_ts)
        
        if filters.to_ts:
            statement = statement.where(HistoryEvent.timestamp <= filters.to_ts)
        
        if filters.location:
            statement = statement.where(HistoryEvent.location == filters.location.serialize_for_db())
        
        if filters.locations:
            location_values = [loc.serialize_for_db() for loc in filters.locations]
            statement = statement.where(HistoryEvent.location.in_(location_values))
        
        if filters.asset:
            statement = statement.where(HistoryEvent.asset == filters.asset)
        
        if filters.assets:
            statement = statement.where(HistoryEvent.asset.in_(filters.assets))
        
        if filters.event_types:
            statement = statement.where(HistoryEvent.type.in_(filters.event_types))
        
        if filters.event_subtypes:
            statement = statement.where(HistoryEvent.subtype.in_(filters.event_subtypes))
        
        if filters.entry_types:
            entry_type_values = [et.serialize_for_db() for et in filters.entry_types]
            statement = statement.where(HistoryEvent.entry_type.in_(entry_type_values))
        
        if filters.exclude_ignored:
            statement = statement.where(HistoryEvent.ignored == 0)
        
        # Address filter - check both location_label and evm_events_info.address
        if filters.addresses:
            statement = statement.outerjoin(EvmEventInfo)
            address_conditions = [
                HistoryEvent.location_label.in_(filters.addresses),
                EvmEventInfo.address.in_(filters.addresses),
            ]
            statement = statement.where(or_(*address_conditions))
        
        # EVM-specific filters
        if any([filters.tx_hashes, filters.counterparties, filters.products]):
            if EvmEventInfo not in [t.entity for t in statement.froms]:
                statement = statement.outerjoin(EvmEventInfo)
            
            if filters.tx_hashes:
                statement = statement.where(EvmEventInfo.tx_hash.in_(filters.tx_hashes))
            
            if filters.counterparties:
                statement = statement.where(EvmEventInfo.counterparty.in_(filters.counterparties))
            
            if filters.products:
                statement = statement.where(EvmEventInfo.product.in_(filters.products))
        
        return statement
    
    def get_history_events(
        self,
        filters: HistoryEventFilter,
        limit: int | None = None,
        offset: int = 0,
        ascending: bool = True,
        group_by_event_ids: bool = False,
        has_premium: bool = True,
    ) -> list[HistoryEvent]:
        """Get history events with advanced filtering.
        
        This is the main query method that replaces the complex get_history_events
        from the old DBHistoryEvents class.
        """
        statement = select(HistoryEvent)
        
        # Apply filters
        statement = self._apply_filters(statement, filters)
        
        # Apply ordering
        if ascending:
            statement = statement.order_by(
                HistoryEvent.timestamp.asc(),
                HistoryEvent.sequence_index.asc(),
            )
        else:
            statement = statement.order_by(
                HistoryEvent.timestamp.desc(),
                HistoryEvent.sequence_index.desc(),
            )
        
        # Handle grouping by event IDs
        if group_by_event_ids:
            # For group by event IDs, we need to limit by unique event_identifiers
            # This requires a subquery
            subquery = (
                select(HistoryEvent.event_identifier)
                .distinct()
                .subquery()
            )
            
            if not has_premium:
                # Apply limit to the subquery for free users
                subquery = (
                    select(HistoryEvent.event_identifier)
                    .distinct()
                    .limit(FREE_HISTORY_EVENTS_LIMIT)
                    .subquery()
                )
            
            statement = statement.where(
                HistoryEvent.event_identifier.in_(select(subquery.c.event_identifier))
            )
        else:
            # Regular limit/offset
            if limit:
                statement = statement.limit(limit)
            elif not has_premium:
                statement = statement.limit(FREE_HISTORY_EVENTS_LIMIT)
            
            if offset:
                statement = statement.offset(offset)
        
        results = self.session.exec(statement)
        return list(results.all())
    
    def get_history_events_count(
        self,
        filters: HistoryEventFilter,
        group_by_event_ids: bool = False,
        has_premium: bool = True,
    ) -> tuple[int, int]:
        """Get count of history events.
        
        Returns:
            Tuple of (count_with_limit, count_without_limit)
        """
        # Base count query
        if group_by_event_ids:
            # Count distinct event identifiers
            count_statement = select(func.count(func.distinct(HistoryEvent.event_identifier)))
        else:
            # Count all events
            count_statement = select(func.count(HistoryEvent.identifier))
        
        # Apply filters
        count_statement = self._apply_filters(count_statement, filters)
        
        # Get total count without limit
        total_count = self.session.exec(count_statement).one()
        
        # Get count with limit for free users
        if has_premium:
            limited_count = total_count
        else:
            if group_by_event_ids:
                # For grouped events, limit applies to event identifiers
                limited_statement = (
                    select(func.count())
                    .select_from(
                        select(HistoryEvent.event_identifier)
                        .distinct()
                        .limit(FREE_HISTORY_EVENTS_LIMIT)
                        .subquery()
                    )
                )
                limited_count = min(total_count, self.session.exec(limited_statement).one())
            else:
                limited_count = min(total_count, FREE_HISTORY_EVENTS_LIMIT)
        
        return limited_count, total_count
    
    def add_history_event(
        self,
        event: HistoryEvent,
        mapping_values: dict[str, int] | None = None,
    ) -> int | None:
        """Add a history event and return its identifier.
        
        Returns None if the event already exists.
        """
        try:
            self.session.add(event)
            self.session.commit()
            self.session.refresh(event)
            
            # Add any mapping values
            if mapping_values:
                for name, value in mapping_values.items():
                    mapping = HistoryEventMapping(
                        parent_identifier=event.identifier,
                        name=name,
                        value=value,
                    )
                    self.session.add(mapping)
                self.session.commit()
            
            return event.identifier
        except Exception:
            self.session.rollback()
            return None
    
    def edit_history_event(
        self,
        event: HistoryEvent,
        mark_customized: bool = True,
    ) -> None:
        """Edit an existing history event."""
        self.session.add(event)
        
        if mark_customized:
            # Check if customized mapping exists
            existing_mapping = self.session.exec(
                select(HistoryEventMapping).where(
                    (HistoryEventMapping.parent_identifier == event.identifier) &
                    (HistoryEventMapping.name == HISTORY_MAPPING_KEY_STATE) &
                    (HistoryEventMapping.value == HISTORY_MAPPING_STATE_CUSTOMIZED)
                )
            ).first()
            
            if not existing_mapping:
                # Add customized mapping
                mapping = HistoryEventMapping(
                    parent_identifier=event.identifier,
                    name=HISTORY_MAPPING_KEY_STATE,
                    value=HISTORY_MAPPING_STATE_CUSTOMIZED,
                )
                self.session.add(mapping)
        
        self.session.commit()
    
    def delete_events_by_tx_hash(
        self,
        tx_hashes: list[bytes],
        location: Location,
        delete_customized: bool = False,
    ) -> None:
        """Delete events by transaction hash, optionally preserving customized events."""
        # Find customized event IDs if needed
        customized_ids = []
        if not delete_customized:
            customized_query = (
                select(HistoryEventMapping.parent_identifier)
                .where(
                    (HistoryEventMapping.name == HISTORY_MAPPING_KEY_STATE) &
                    (HistoryEventMapping.value == HISTORY_MAPPING_STATE_CUSTOMIZED)
                )
            )
            customized_ids = list(self.session.exec(customized_query).all())
        
        # Build delete query
        delete_query = (
            select(HistoryEvent)
            .join(EvmEventInfo)
            .where(
                (EvmEventInfo.tx_hash.in_(tx_hashes)) &
                (HistoryEvent.location == location.serialize_for_db())
            )
        )
        
        if customized_ids:
            delete_query = delete_query.where(
                HistoryEvent.identifier.notin_(customized_ids)
            )
        
        # Execute delete
        events_to_delete = self.session.exec(delete_query).all()
        for event in events_to_delete:
            self.session.delete(event)
        
        self.session.commit()
    
    def get_customized_event_identifiers(
        self,
        location: Location | None = None,
    ) -> list[int]:
        """Get identifiers of all customized events."""
        query = (
            select(HistoryEventMapping.parent_identifier)
            .where(
                (HistoryEventMapping.name == HISTORY_MAPPING_KEY_STATE) &
                (HistoryEventMapping.value == HISTORY_MAPPING_STATE_CUSTOMIZED)
            )
        )
        
        if location:
            query = (
                query.join(HistoryEvent)
                .where(HistoryEvent.location == location.serialize_for_db())
            )
        
        return list(self.session.exec(query).all())
    
    def find_missing_prices(
        self,
        from_ts: Timestamp | None = None,
        to_ts: Timestamp | None = None,
    ) -> list[tuple[str, Timestamp]]:
        """Find events with missing USD prices.
        
        Returns:
            List of tuples (asset_identifier, timestamp) for events missing prices
        """
        query = (
            select(HistoryEvent.asset, HistoryEvent.timestamp)
            .distinct()
            .where(
                (HistoryEvent.usd_value == None) &
                (cast(HistoryEvent.amount, text) != '0')
            )
        )
        
        if from_ts:
            query = query.where(HistoryEvent.timestamp >= from_ts)
        
        if to_ts:
            query = query.where(HistoryEvent.timestamp <= to_ts)
        
        results = self.session.exec(query)
        return [(asset, Timestamp(ts)) for asset, ts in results.all()]
    
    def get_events_by_location_and_period(
        self,
        location: Location,
        from_ts: Timestamp,
        to_ts: Timestamp,
        event_types: list[str] | None = None,
    ) -> list[HistoryEvent]:
        """Get events for a specific location and time period."""
        filters = HistoryEventFilter(
            location=location,
            from_ts=from_ts,
            to_ts=to_ts,
            event_types=event_types,
        )
        return self.get_history_events(filters)
    
    def find_by_event_identifier(self, event_identifier: str) -> list[HistoryEvent]:
        """Find events by event identifier."""
        statement = select(HistoryEvent).where(HistoryEvent.event_identifier == event_identifier)
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_tx_hash(self, tx_hash: bytes) -> list[HistoryEvent]:
        """Find events by transaction hash (for EVM events)."""
        statement = (
            select(HistoryEvent)
            .join(EvmEventInfo)
            .where(EvmEventInfo.tx_hash == tx_hash)
        )
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_address(self, address: str) -> list[HistoryEvent]:
        """Find all events for an address."""
        statement = (
            select(HistoryEvent)
            .outerjoin(EvmEventInfo)
            .where(
                (HistoryEvent.location_label == address) |
                (EvmEventInfo.address == address)
            )
        )
        results = self.session.exec(statement)
        return list(results.all())
    
    def find_by_timestamp_range(
        self,
        start: datetime | Timestamp,
        end: datetime | Timestamp,
        address: str | None = None,
    ) -> list[HistoryEvent]:
        """Find events within a timestamp range."""
        # Convert datetime to timestamp if needed
        start_ts = int(start.timestamp()) if isinstance(start, datetime) else start
        end_ts = int(end.timestamp()) if isinstance(end, datetime) else end
        
        filters = HistoryEventFilter(
            from_ts=start_ts,
            to_ts=end_ts,
            addresses=[address] if address else None,
        )
        return self.get_history_events(filters)
    
    def find_by_type(self, event_type: str, subtype: str | None = None) -> list[HistoryEvent]:
        """Find all events of a specific type."""
        filters = HistoryEventFilter(
            event_types=[event_type],
            event_subtypes=[subtype] if subtype else None,
        )
        return self.get_history_events(filters)
    
    def find_by(self, **kwargs: Any) -> list[HistoryEvent]:
        """Find events by multiple criteria."""
        statement = select(HistoryEvent)
        
        for key, value in kwargs.items():
            if hasattr(HistoryEvent, key):
                statement = statement.where(getattr(HistoryEvent, key) == value)
        
        results = self.session.exec(statement)
        return list(results.all())
    
    def get_latest_events(self, limit: int = 100) -> list[HistoryEvent]:
        """Get the latest events."""
        filters = HistoryEventFilter()
        return self.get_history_events(filters, limit=limit, ascending=False)
    
    def exists_by_event_identifier(self, event_identifier: str) -> bool:
        """Check if event exists by event identifier."""
        return len(self.find_by_event_identifier(event_identifier)) > 0
    
    def get_ignored_events(self) -> list[HistoryEvent]:
        """Get all ignored events."""
        statement = select(HistoryEvent).where(HistoryEvent.ignored == 1)
        results = self.session.exec(statement)
        return list(results.all())