"""Async HistoryEvents repository for v2 API.

Handles all history events-related async database operations.
"""
from typing import TYPE_CHECKING, Any, Optional, overload

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import text

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotkehlchen.db.constants import (
    ETH_STAKING_EVENT_FIELDS,
    ETH_STAKING_FIELD_LENGTH,
    EVM_EVENT_FIELDS,
    EVM_FIELD_LENGTH,
    HISTORY_BASE_ENTRY_FIELDS,
    HISTORY_BASE_ENTRY_LENGTH,
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.db.filtering import (
    ALL_EVENTS_DATA_JOIN,
    EVM_EVENT_JOIN,
    EthDepositEventFilterQuery,
    EthWithdrawalFilterQuery,
    EvmEventFilterQuery,
    HistoryBaseEntryFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEvent,
)
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    Location,
    Timestamp,
    TimestampMS,
)

# Constants
FREE_HISTORY_EVENTS_LIMIT = 100  # Default limit for free users

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class HistoryEventsRepository:
    """Async repository for history events.
    
    Note: This is not a typical SQLModel repository as history events
    use a complex multi-table structure that doesn't map cleanly to
    SQLModel models. Raw SQL is used throughout this repository because:
    
    1. History events use a polymorphic multi-table inheritance pattern
    2. Complex JOINs are required between history_events, evm_events_info, 
       eth_staking_events_info, and history_events_mappings tables
    3. Dynamic filter queries with variable WHERE clauses
    4. Performance-critical operations requiring specific SQL optimizations
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_history_event(
        self,
        event: HistoryBaseEntry,
        mapping_values: dict[str, int] | None = None,
    ) -> int | None:
        """Insert a single history entry to the DB. Returns its identifier or
        None if it already exists. This function serializes the event depending
        on type to the appropriate DB tables.

        Optionally map it to a specific value used to map attributes
        to some events

        May raise:
        - DeserializationError if the event could not be serialized for the DB
        - IntegrityError: If the asset of the added history event does not exist in
        the DB. Can only happen if an event with an unresolved asset is passed.
        """
        identifier = None
        
        # Insert into history_events base table
        serialized = event.serialize_for_db()
        
        # Note: Raw SQL required for ON CONFLICT DO NOTHING RETURNING pattern
        query = text("""
            INSERT INTO history_events (
                event_identifier, sequence_index, timestamp, location, location_label,
                asset, amount, usd_value, notes, type, subtype
            ) VALUES (
                :event_identifier, :sequence_index, :timestamp, :location, :location_label,
                :asset, :amount, :usd_value, :notes, :type, :subtype
            ) ON CONFLICT DO NOTHING RETURNING identifier
        """)
        
        result = await self.session.execute(query, {
            'event_identifier': serialized[0],
            'sequence_index': serialized[1],
            'timestamp': serialized[2],
            'location': serialized[3],
            'location_label': serialized[4],
            'asset': serialized[5],
            'amount': serialized[6],
            'usd_value': serialized[7],
            'notes': serialized[8],
            'type': serialized[9],
            'subtype': serialized[10],
        })
        
        row = result.fetchone()
        if row:
            identifier = row[0]
            
            # Handle type-specific data
            await self._add_type_specific_data(event, identifier)
            
            # Handle mapping values
            if mapping_values and identifier:
                for key, value in mapping_values.items():
                    await self.session.execute(
                        text("""
                            INSERT OR IGNORE INTO history_events_mappings (
                                parent_identifier, name, value
                            ) VALUES (:parent_id, :name, :value)
                        """),
                        {'parent_id': identifier, 'name': key, 'value': value}
                    )
        
        await self.session.commit()
        return identifier
    
    async def _add_type_specific_data(
        self,
        event: HistoryBaseEntry,
        identifier: int,
    ) -> None:
        """Add type-specific data for the event."""
        if event.entry_type == HistoryBaseEntryType.EVM_EVENT:
            # Add EVM event specific data
            evm_event = event  # type: EvmEvent
            query = text("""
                INSERT INTO evm_events_info (
                    identifier, tx_hash, counterparty, product, address
                ) VALUES (
                    :identifier, :tx_hash, :counterparty, :product, :address
                )
            """)
            await self.session.execute(query, {
                'identifier': identifier,
                'tx_hash': evm_event.tx_hash.hex(),
                'counterparty': evm_event.counterparty,
                'product': evm_event.product,
                'address': evm_event.address,
            })
        elif event.entry_type == HistoryBaseEntryType.ETH_STAKING_EVENT:
            # Add ETH staking event specific data
            if isinstance(event, EthDepositEvent):
                query = text("""
                    INSERT INTO eth_staking_events_info (
                        identifier, validator_index, is_exit_or_blocknumber
                    ) VALUES (
                        :identifier, :validator_index, :deposit_index
                    )
                """)
                await self.session.execute(query, {
                    'identifier': identifier,
                    'validator_index': event.validator_index,
                    'deposit_index': event.deposit_index,
                })
            elif isinstance(event, (EthWithdrawalEvent, EthBlockEvent)):
                query = text("""
                    INSERT INTO eth_staking_events_info (
                        identifier, validator_index, is_exit_or_blocknumber
                    ) VALUES (
                        :identifier, :validator_index, :value
                    )
                """)
                value = 1 if isinstance(event, EthWithdrawalEvent) and event.is_exit else (
                    event.block_number if isinstance(event, EthBlockEvent) else 0
                )
                await self.session.execute(query, {
                    'identifier': identifier,
                    'validator_index': event.validator_index,
                    'value': value,
                })
    
    async def add_history_events(
        self,
        events: list[HistoryBaseEntry],
    ) -> None:
        """Add multiple history events efficiently.
        
        May raise:
        - DeserializationError
        - IntegrityError
        """
        for event in events:
            await self.add_history_event(event)
    
    async def edit_history_event(self, event: HistoryBaseEntry) -> None:
        """Edit an existing history event.
        
        May raise:
        - DeserializationError
        """
        serialized = event.serialize_for_db()
        
        query = text("""
            UPDATE history_events SET
                event_identifier = :event_identifier,
                sequence_index = :sequence_index,
                timestamp = :timestamp,
                location = :location,
                location_label = :location_label,
                asset = :asset,
                amount = :amount,
                usd_value = :usd_value,
                notes = :notes,
                type = :type,
                subtype = :subtype
            WHERE identifier = :identifier
        """)
        
        await self.session.execute(query, {
            'identifier': event.identifier,
            'event_identifier': serialized[0],
            'sequence_index': serialized[1],
            'timestamp': serialized[2],
            'location': serialized[3],
            'location_label': serialized[4],
            'asset': serialized[5],
            'amount': serialized[6],
            'usd_value': serialized[7],
            'notes': serialized[8],
            'type': serialized[9],
            'subtype': serialized[10],
        })
        
        # Update type-specific data
        await self._update_type_specific_data(event)
        
        # Mark as customized
        await self.session.execute(
            text("""
                INSERT INTO history_events_mappings (parent_identifier, name, value)
                VALUES (:identifier, :key, :value)
                ON CONFLICT(parent_identifier, name) DO UPDATE SET value = :value
            """),
            {
                'identifier': event.identifier,
                'key': HISTORY_MAPPING_KEY_STATE,
                'value': HISTORY_MAPPING_STATE_CUSTOMIZED,
            }
        )
        
        await self.session.commit()
    
    async def _update_type_specific_data(self, event: HistoryBaseEntry) -> None:
        """Update type-specific data for the event."""
        if event.entry_type == HistoryBaseEntryType.EVM_EVENT:
            evm_event = event  # type: EvmEvent
            query = text("""
                UPDATE evm_events_info SET
                    tx_hash = :tx_hash,
                    counterparty = :counterparty,
                    product = :product,
                    address = :address
                WHERE identifier = :identifier
            """)
            await self.session.execute(query, {
                'identifier': event.identifier,
                'tx_hash': evm_event.tx_hash.hex(),
                'counterparty': evm_event.counterparty,
                'product': evm_event.product,
                'address': evm_event.address,
            })
    
    async def delete_history_events_by_identifier(
        self,
        identifiers: list[int],
    ) -> None:
        """Delete history events by their identifiers."""
        if not identifiers:
            return
        
        # Delete from mapping tables first
        await self.session.execute(
            text("DELETE FROM history_events_mappings WHERE parent_identifier IN :ids"),
            {'ids': tuple(identifiers)}
        )
        
        # Delete from type-specific tables
        await self.session.execute(
            text("DELETE FROM evm_events_info WHERE identifier IN :ids"),
            {'ids': tuple(identifiers)}
        )
        await self.session.execute(
            text("DELETE FROM eth_staking_events_info WHERE identifier IN :ids"),
            {'ids': tuple(identifiers)}
        )
        
        # Delete from main table
        await self.session.execute(
            text("DELETE FROM history_events WHERE identifier IN :ids"),
            {'ids': tuple(identifiers)}
        )
        
        await self.session.commit()
    
    async def get_history_events(
        self,
        filter_query: HistoryEventFilterQuery,
        has_premium: bool = True,
        group_by_event_ids: bool = False,
    ) -> list[HistoryBaseEntry]:
        """Get history events based on filter criteria.
        
        Returns a list of history events matching the filter.
        """
        query_str, bindings = filter_query.prepare()
        
        if not has_premium:
            query_str += f' LIMIT {FREE_HISTORY_EVENTS_LIMIT}'
        
        # Build the full query
        # Note: Complex multi-table JOINs with dynamic fields require raw SQL
        if isinstance(filter_query, EvmEventFilterQuery):
            base_query = f"""
                SELECT
                    {', '.join(HISTORY_BASE_ENTRY_FIELDS)},
                    {', '.join(EVM_EVENT_FIELDS)}
                FROM history_events
                INNER JOIN evm_events_info ON history_events.identifier = evm_events_info.identifier
                {query_str}
            """
        elif isinstance(filter_query, (EthDepositEventFilterQuery, EthWithdrawalFilterQuery)):
            base_query = f"""
                SELECT
                    {', '.join(HISTORY_BASE_ENTRY_FIELDS)},
                    {', '.join(ETH_STAKING_EVENT_FIELDS)}
                FROM history_events
                INNER JOIN eth_staking_events_info ON history_events.identifier = eth_staking_events_info.identifier
                {query_str}
            """
        else:
            base_query = f"""
                SELECT
                    {', '.join(HISTORY_BASE_ENTRY_FIELDS)}
                FROM history_events
                {query_str}
            """
        
        result = await self.session.execute(text(base_query), bindings)
        rows = result.fetchall()
        
        events = []
        for row in rows:
            try:
                event = self._deserialize_history_event(row, filter_query)
                if event:
                    events.append(event)
            except DeserializationError:
                continue
        
        return events
    
    def _deserialize_history_event(
        self,
        row: tuple,
        filter_query: HistoryEventFilterQuery,
    ) -> HistoryBaseEntry | None:
        """Deserialize a database row to a history event object."""
        # This is a simplified version - full implementation would handle
        # all event types properly
        base_data = row[:HISTORY_BASE_ENTRY_LENGTH]
        
        # Determine event type and deserialize accordingly
        entry_type = HistoryBaseEntryType.deserialize(base_data[11])
        
        if entry_type == HistoryBaseEntryType.HISTORY_EVENT:
            return HistoryEvent.deserialize_from_db(base_data)
        elif entry_type == HistoryBaseEntryType.EVM_EVENT:
            if len(row) >= HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH:
                evm_data = row[HISTORY_BASE_ENTRY_LENGTH:HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH]
                return EvmEvent.deserialize_from_db(base_data + evm_data)
        # Add other event types as needed
        
        return None
    
    async def get_event_by_identifier(self, identifier: int) -> HistoryBaseEntry | None:
        """Get a single event by its identifier."""
        events = await self.get_history_events(
            HistoryEventFilterQuery.make(event_identifiers=[identifier]),
            has_premium=True,
        )
        return events[0] if events else None
    
    async def get_evm_event_by_identifier(self, identifier: int) -> EvmEvent | None:
        """Get a single EVM event by its identifier."""
        event = await self.get_event_by_identifier(identifier)
        if event and isinstance(event, EvmEvent):
            return event
        return None
    
    async def get_customized_event_identifiers(
        self,
        chain_id: ChainID | None = None,
    ) -> list[int]:
        """Get identifiers of all customized events."""
        if chain_id is not None:
            query = text("""
                SELECT hm.parent_identifier
                FROM history_events_mappings hm
                INNER JOIN history_events he ON hm.parent_identifier = he.identifier
                WHERE hm.name = :key AND hm.value = :value
                AND he.location = :location
            """)
            params = {
                'key': HISTORY_MAPPING_KEY_STATE,
                'value': HISTORY_MAPPING_STATE_CUSTOMIZED,
                'location': chain_id.to_blockchain().value,
            }
        else:
            query = text("""
                SELECT parent_identifier
                FROM history_events_mappings
                WHERE name = :key AND value = :value
            """)
            params = {
                'key': HISTORY_MAPPING_KEY_STATE,
                'value': HISTORY_MAPPING_STATE_CUSTOMIZED,
            }
        
        result = await self.session.execute(query, params)
        return [row[0] for row in result.fetchall()]
    
    async def count(self, filter_query: HistoryEventFilterQuery | None = None) -> int:
        """Count history events matching the filter."""
        if filter_query:
            query_str, bindings = filter_query.prepare(with_pagination=False)
            query = text(f"SELECT COUNT(*) FROM history_events {query_str}")
            result = await self.session.execute(query, bindings)
        else:
            result = await self.session.execute(text("SELECT COUNT(*) FROM history_events"))
        
        return result.scalar() or 0
    
    async def get_history_events_and_limit_info(
        self,
        filter_query: HistoryEventFilterQuery,
        has_premium: bool = True,
        group_by_event_ids: bool = False,
    ) -> tuple[list[HistoryBaseEntry], int, int]:
        """Get history events with count information.
        
        Returns:
            - List of events
            - Total count without limit
            - Count with limit applied (for free users)
        """
        # Get total count without limit
        total_count = await self.count(filter_query)
        
        # Get events
        events = await self.get_history_events(
            filter_query=filter_query,
            has_premium=has_premium,
            group_by_event_ids=group_by_event_ids,
        )
        
        # For free users, the limited count is the actual number of events returned
        limited_count = len(events) if not has_premium else total_count
        
        return events, total_count, limited_count
    
    async def get_events_by_location_and_type(
        self,
        location: Location,
        event_type: str | None = None,
        event_subtype: str | None = None,
    ) -> list[HistoryBaseEntry]:
        """Get events filtered by location and optionally type/subtype."""
        query_parts = ["WHERE location = :location"]
        params = {'location': location.value}
        
        if event_type is not None:
            query_parts.append("AND type = :type")
            params['type'] = event_type
            
        if event_subtype is not None:
            query_parts.append("AND subtype = :subtype")
            params['subtype'] = event_subtype
        
        query = text(f"""
            SELECT {', '.join(HISTORY_BASE_ENTRY_FIELDS)}
            FROM history_events
            {' '.join(query_parts)}
            ORDER BY timestamp DESC, sequence_index ASC
        """)
        
        result = await self.session.execute(query, params)
        rows = result.fetchall()
        
        events = []
        for row in rows:
            try:
                event = HistoryEvent.deserialize_from_db(row[:HISTORY_BASE_ENTRY_LENGTH])
                events.append(event)
            except DeserializationError:
                continue
                
        return events
    
    async def get_base_entries_missing_prices(
        self,
        query_filter: HistoryEventFilterQuery,
    ) -> list[tuple[str, Timestamp]]:
        """Get assets and timestamps for events missing USD prices.
        
        Returns:
            List of (asset_identifier, timestamp) tuples
        """
        filter_str, bindings = filter_query.prepare(with_pagination=False)
        
        query = text(f"""
            SELECT DISTINCT asset, timestamp
            FROM history_events
            {filter_str}
            AND usd_value IS NULL
            AND asset IS NOT NULL
            ORDER BY timestamp
        """)
        
        result = await self.session.execute(query, bindings)
        return [(row[0], Timestamp(row[1])) for row in result.fetchall()]
    
    async def get_amount_stats(
        self,
        filter_query: HistoryEventFilterQuery,
    ) -> dict[str, str]:
        """Get sum of amounts grouped by asset.
        
        Returns:
            Dict mapping asset identifier to total amount as string
        """
        filter_str, bindings = filter_query.prepare(with_pagination=False)
        
        query = text(f"""
            SELECT asset, SUM(CAST(amount AS REAL))
            FROM history_events
            {filter_str}
            AND asset IS NOT NULL
            GROUP BY asset
        """)
        
        result = await self.session.execute(query, bindings)
        return {row[0]: str(row[1]) for row in result.fetchall()}
    
    async def get_event_identifiers_for_tx_hash(
        self,
        tx_hash: EVMTxHash,
    ) -> list[int]:
        """Get all event identifiers for a given transaction hash."""
        query = text("""
            SELECT he.identifier
            FROM history_events he
            INNER JOIN evm_events_info eei ON he.identifier = eei.identifier
            WHERE eei.tx_hash = :tx_hash
            ORDER BY he.sequence_index
        """)
        
        result = await self.session.execute(query, {'tx_hash': tx_hash.hex()})
        return [row[0] for row in result.fetchall()]
    
    async def get_events_by_event_identifier(
        self,
        event_identifier: str,
    ) -> list[HistoryBaseEntry]:
        """Get all events with a specific event_identifier.
        
        This groups together related events (e.g., all events from a single transaction).
        """
        query = text(f"""
            SELECT
                {', '.join(HISTORY_BASE_ENTRY_FIELDS)},
                {', '.join(EVM_EVENT_FIELDS)}
            FROM history_events
            LEFT JOIN evm_events_info ON history_events.identifier = evm_events_info.identifier
            WHERE event_identifier = :event_id
            ORDER BY sequence_index
        """)
        
        result = await self.session.execute(query, {'event_id': event_identifier})
        rows = result.fetchall()
        
        events = []
        for row in rows:
            try:
                # Check if we have EVM data
                if row[HISTORY_BASE_ENTRY_LENGTH] is not None:
                    event = EvmEvent.deserialize_from_db(
                        row[:HISTORY_BASE_ENTRY_LENGTH] + 
                        row[HISTORY_BASE_ENTRY_LENGTH:HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH]
                    )
                else:
                    event = HistoryEvent.deserialize_from_db(row[:HISTORY_BASE_ENTRY_LENGTH])
                events.append(event)
            except DeserializationError:
                continue
                
        return events
    
    async def get_associated_event_data(
        self,
        identifier: int,
        event_type: HistoryBaseEntryType,
    ) -> dict[str, Any] | None:
        """Get type-specific data for an event."""
        if event_type == HistoryBaseEntryType.EVM_EVENT:
            query = text("""
                SELECT tx_hash, counterparty, product, address
                FROM evm_events_info
                WHERE identifier = :id
            """)
            result = await self.session.execute(query, {'id': identifier})
            row = result.fetchone()
            if row:
                return {
                    'tx_hash': row[0],
                    'counterparty': row[1],
                    'product': row[2],
                    'address': row[3],
                }
        elif event_type in (
            HistoryBaseEntryType.ETH_DEPOSIT_EVENT,
            HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT,
            HistoryBaseEntryType.ETH_BLOCK_EVENT,
        ):
            query = text("""
                SELECT validator_index, is_exit_or_blocknumber
                FROM eth_staking_events_info
                WHERE identifier = :id
            """)
            result = await self.session.execute(query, {'id': identifier})
            row = result.fetchone()
            if row:
                return {
                    'validator_index': row[0],
                    'is_exit_or_blocknumber': row[1],
                }
        
        return None

    async def get_defi_events_by_protocol(
        self,
        protocol: str,
        account: str | None = None,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[HistoryEvent]:
        """Get DeFi events for a specific protocol.
        
        Args:
            protocol: The DeFi protocol name (e.g., 'uniswap', 'aave', 'compound')
            account: Optional account address filter
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of DeFi history events
        """
        from rotki2.db.models.user.history import EvmEventInfo
        
        query = select(HistoryEvent).join(
            EvmEventInfo,
            HistoryEvent.identifier == EvmEventInfo.identifier
        ).where(
            col(EvmEventInfo.counterparty) == protocol
        )
        
        if account:
            query = query.where(col(HistoryEvent.location_label) == account)
        if start_timestamp:
            query = query.where(col(HistoryEvent.timestamp) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(HistoryEvent.timestamp) <= end_timestamp)
            
        query = query.order_by(HistoryEvent.timestamp.desc())
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_liquidity_events(
        self,
        account: str | None = None,
        event_types: list[str] | None = None,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[HistoryEvent]:
        """Get liquidity-related events (add/remove liquidity).
        
        Args:
            account: Optional account address filter
            event_types: Optional list of event types to filter (e.g., ['deposit', 'withdrawal'])
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of liquidity history events
        """
        from rotki2.db.models.user.enums import HistoryEventSubType
        
        # Default liquidity event types
        if event_types is None:
            event_types = [
                HistoryEventSubType.DEPOSIT_ASSET,
                HistoryEventSubType.REMOVE_ASSET,
                HistoryEventSubType.RECEIVE_WRAPPED,
                HistoryEventSubType.RETURN_WRAPPED,
            ]
        
        query = select(HistoryEvent).where(
            col(HistoryEvent.event_subtype).in_(event_types)
        )
        
        if account:
            query = query.where(col(HistoryEvent.location_label) == account)
        if start_timestamp:
            query = query.where(col(HistoryEvent.timestamp) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(HistoryEvent.timestamp) <= end_timestamp)
            
        query = query.order_by(HistoryEvent.timestamp.desc())
        
        result = await self.session.exec(query)
        return list(result.all())

    async def get_protocol_volume_stats(
        self,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[dict[str, str]]:
        """Get transaction volume statistics grouped by DeFi protocol.
        
        Args:
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of dicts with protocol, event_count, and unique_addresses
        """
        from rotki2.db.models.user.history import EvmEventInfo
        from sqlalchemy import func
        
        query = select(
            EvmEventInfo.counterparty,
            func.count(HistoryEvent.identifier).label('event_count'),
            func.count(func.distinct(HistoryEvent.location_label)).label('unique_addresses'),
        ).join(
            HistoryEvent,
            EvmEventInfo.identifier == HistoryEvent.identifier
        ).where(
            col(EvmEventInfo.counterparty).is_not(None)
        ).group_by(EvmEventInfo.counterparty)
        
        if start_timestamp:
            query = query.where(col(HistoryEvent.timestamp) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(HistoryEvent.timestamp) <= end_timestamp)
        
        result = await self.session.exec(query)
        
        return [
            {
                'protocol': row[0],
                'event_count': str(row[1]),
                'unique_addresses': str(row[2]),
            }
            for row in result.all()
        ]

    async def get_lending_events(
        self,
        account: str | None = None,
        protocol: str | None = None,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[HistoryEvent]:
        """Get lending/borrowing events from DeFi protocols.
        
        Args:
            account: Optional account address filter
            protocol: Optional protocol filter (e.g., 'aave', 'compound')
            start_timestamp: Optional start timestamp
            end_timestamp: Optional end timestamp
            
        Returns:
            List of lending/borrowing history events
        """
        from rotki2.db.models.user.enums import HistoryEventSubType
        from rotki2.db.models.user.history import EvmEventInfo
        
        lending_subtypes = [
            HistoryEventSubType.DEPOSIT_ASSET,
            HistoryEventSubType.REMOVE_ASSET,
            HistoryEventSubType.BORROW,
            HistoryEventSubType.PAYBACK_DEBT,
            HistoryEventSubType.LIQUIDATE,
            HistoryEventSubType.GENERATE_DEBT,
            HistoryEventSubType.RECEIVE_WRAPPED,
        ]
        
        query = select(HistoryEvent).where(
            col(HistoryEvent.event_subtype).in_(lending_subtypes)
        )
        
        if protocol:
            query = query.join(
                EvmEventInfo,
                HistoryEvent.identifier == EvmEventInfo.identifier
            ).where(col(EvmEventInfo.counterparty) == protocol)
        
        if account:
            query = query.where(col(HistoryEvent.location_label) == account)
        if start_timestamp:
            query = query.where(col(HistoryEvent.timestamp) >= start_timestamp)
        if end_timestamp:
            query = query.where(col(HistoryEvent.timestamp) <= end_timestamp)
            
        query = query.order_by(HistoryEvent.timestamp.desc())
        
        result = await self.session.exec(query)
        return list(result.all())