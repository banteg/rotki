"""Repository for history events management"""


from sqlalchemy import delete, func, select

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.orm.history_events import (
    EvmEventInfo,
    HistoryEvent,
    HistoryEventMapping,
    SkippedExternalEvent,
)
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent as HistoryEventData
from rotkehlchen.types import EVMTxHash, Location, Timestamp


class HistoryEventRepository(BaseRepository[HistoryEvent]):
    """Repository for managing history events"""

    def __init__(self, session):
        super().__init__(session, HistoryEvent)

    def add_event(
        self,
        event_data: HistoryEventData,
    ) -> HistoryEvent:
        """Add a history event"""
        event = HistoryEvent(
            entry_type=event_data.entry_type.value,
            event_identifier=event_data.event_identifier,
            sequence_index=event_data.sequence_index,
            timestamp=int(event_data.timestamp),
            location=event_data.location.serialize_for_db(),
            location_label=event_data.location_label,
            asset=event_data.asset.identifier,
            amount=str(event_data.balance.amount),
            notes=event_data.notes,
            type=event_data.event_type,
            subtype=event_data.event_subtype,
            extra_data=event_data.extra_data,
            ignored=False,
        )
        return self.add(event)

    def get_events(
        self,
        event_identifiers: list[str] | None = None,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
        locations: list[Location] | None = None,
        event_types: list[str] | None = None,
        event_subtypes: list[str] | None = None,
        assets: list[Asset] | None = None,
        ignored: bool | None = None,
        exclude_ignored: bool = True,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[HistoryEvent]:
        """Get history events with filters"""
        query = select(HistoryEvent)

        # Apply filters
        if event_identifiers:
            query = query.filter(HistoryEvent.event_identifier.in_(event_identifiers))

        if from_timestamp is not None:
            query = query.filter(HistoryEvent.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(HistoryEvent.timestamp <= int(to_timestamp))

        if locations:
            location_chars = [loc.serialize_for_db() for loc in locations]
            query = query.filter(HistoryEvent.location.in_(location_chars))

        if event_types:
            query = query.filter(HistoryEvent.type.in_(event_types))

        if event_subtypes:
            query = query.filter(HistoryEvent.subtype.in_(event_subtypes))

        if assets:
            asset_ids = [asset.identifier for asset in assets]
            query = query.filter(HistoryEvent.asset.in_(asset_ids))

        if ignored is not None:
            query = query.filter_by(ignored=ignored)
        elif exclude_ignored:
            query = query.filter_by(ignored=False)

        # Order by timestamp and sequence
        query = query.order_by(
            HistoryEvent.timestamp.desc(),
            HistoryEvent.sequence_index.desc(),
        )

        # Apply pagination
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def get_event_by_id(self, event_id: int) -> HistoryEvent | None:
        """Get a specific event by ID"""
        return self.get(identifier=event_id)

    def update_event(
        self,
        event_id: int,
        timestamp: Timestamp | None = None,
        location_label: str | None = None,
        notes: str | None = None,
        amount: FVal | None = None,
        ignored: bool | None = None,
    ) -> HistoryEvent | None:
        """Update a history event"""
        event = self.get_event_by_id(event_id)
        if not event:
            return None

        if timestamp is not None:
            event.timestamp = int(timestamp)
        if location_label is not None:
            event.location_label = location_label
        if notes is not None:
            event.notes = notes
        if amount is not None:
            event.amount = str(amount)
        if ignored is not None:
            event.ignored = ignored

        return self.update(event)

    def delete_event(self, event_id: int) -> bool:
        """Delete a history event"""
        return self.delete_by(identifier=event_id) > 0

    def delete_events_by_identifier(self, event_identifier: str) -> int:
        """Delete all events with a specific identifier"""
        stmt = delete(HistoryEvent).filter_by(event_identifier=event_identifier)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def get_events_count(
        self,
        event_identifiers: list[str] | None = None,
        ignored: bool | None = None,
    ) -> int:
        """Get count of history events"""
        query = select(func.count()).select_from(HistoryEvent)

        if event_identifiers:
            query = query.filter(HistoryEvent.event_identifier.in_(event_identifiers))

        if ignored is not None:
            query = query.filter_by(ignored=ignored)

        return self.session.execute(query).scalar() or 0

    # EVM event info operations

    def add_evm_event_info(
        self,
        event_id: int,
        tx_hash: EVMTxHash,
        counterparty: str | None = None,
        product: str | None = None,
        address: str | None = None,
    ) -> EvmEventInfo:
        """Add EVM-specific event information"""
        info = EvmEventInfo(
            identifier=event_id,
            tx_hash=tx_hash,
            counterparty=counterparty,
            product=product,
            address=address,
        )
        self.session.add(info)
        self.session.flush()
        return info

    def get_evm_events_by_tx_hash(
        self,
        tx_hash: EVMTxHash,
    ) -> list[HistoryEvent]:
        """Get all events for a transaction hash"""
        query = (
            select(HistoryEvent)
            .join(EvmEventInfo)
            .filter(EvmEventInfo.tx_hash == tx_hash)
            .order_by(HistoryEvent.sequence_index)
        )
        return list(self.session.execute(query).scalars().all())

    # Event mapping operations

    def add_event_mapping(
        self,
        event_id: int,
        name: str,
        value: int,
    ) -> HistoryEventMapping:
        """Add an event mapping"""
        mapping = HistoryEventMapping(
            parent_identifier=event_id,
            name=name,
            value=value,
        )
        self.session.add(mapping)
        self.session.flush()
        return mapping

    def get_event_mappings(
        self,
        event_id: int,
        name: str | None = None,
    ) -> list[HistoryEventMapping]:
        """Get mappings for an event"""
        query = select(HistoryEventMapping).filter_by(parent_identifier=event_id)

        if name is not None:
            query = query.filter_by(name=name)

        return list(self.session.execute(query).scalars().all())

    def is_event_customized(self, event_id: int) -> bool:
        """Check if an event has been customized"""
        mappings = self.get_event_mappings(event_id, name='customized')
        return bool(mappings and mappings[0].value == 1)

    # Skipped events operations

    def add_skipped_event(
        self,
        data: str,
        location: Location,
        extra_data: str | None = None,
    ) -> SkippedExternalEvent:
        """Add a skipped external event"""
        event = SkippedExternalEvent(
            data=data,
            location=location.serialize_for_db(),
            extra_data=extra_data,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def get_skipped_events(
        self,
        location: Location | None = None,
    ) -> list[SkippedExternalEvent]:
        """Get skipped external events"""
        if location:
            stmt = select(SkippedExternalEvent).filter_by(
                location=location.serialize_for_db(),
            )
        else:
            stmt = select(SkippedExternalEvent)

        return list(self.session.execute(stmt).scalars().all())

    def skipped_event_exists(
        self,
        data: str,
        location: Location,
    ) -> bool:
        """Check if a skipped event exists"""
        stmt = select(SkippedExternalEvent).filter_by(
            data=data,
            location=location.serialize_for_db(),
        ).limit(1)
        return self.session.execute(stmt).scalar() is not None
