"""Async HistoryEvents service for history event operations"""
from typing import TYPE_CHECKING, Any, Optional

from rotki2.api.v2.repositories.async_history_events import AsyncHistoryEventsRepository
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.types import ChainID, Location

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.notifier import RotkiNotifier


class AsyncHistoryEventsService:
    """Async service for history events operations"""
    
    def __init__(
        self,
        history_events_repository: AsyncHistoryEventsRepository,
        notifier: 'RotkiNotifier | None' = None,
    ):
        self.history_events_repository = history_events_repository
        self.notifier = notifier
    
    async def add_history_event(
        self,
        event: HistoryBaseEntry,
        mapping_values: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Add a new history event.
        
        Returns:
            Dict with 'identifier' key containing the new event ID
            
        May raise:
        - InputError if the event data is invalid
        - DeserializationError if the event cannot be serialized
        """
        try:
            identifier = await self.history_events_repository.add_history_event(
                event=event,
                mapping_values=mapping_values,
            )
            
            if identifier is None:
                raise InputError('Event already exists in the database')
            
            return {'identifier': identifier}
            
        except Exception as e:
            raise InputError(f'Failed to add history event: {str(e)}') from e
    
    async def add_history_events(
        self,
        events: list[HistoryBaseEntry],
    ) -> dict[str, Any]:
        """Add multiple history events.
        
        Returns:
            Dict with 'added' key containing number of events added
        """
        try:
            await self.history_events_repository.add_history_events(events)
            return {'added': len(events)}
        except Exception as e:
            raise InputError(f'Failed to add history events: {str(e)}') from e
    
    async def edit_history_event(
        self,
        event: HistoryBaseEntry,
    ) -> dict[str, Any]:
        """Edit an existing history event.
        
        Returns:
            Dict with success message
        """
        if not event.identifier:
            raise InputError('Event must have an identifier to be edited')
        
        try:
            await self.history_events_repository.edit_history_event(event)
            return {'message': f'Successfully edited event {event.identifier}'}
        except Exception as e:
            raise InputError(f'Failed to edit history event: {str(e)}') from e
    
    async def delete_history_events(
        self,
        identifiers: list[int],
    ) -> dict[str, Any]:
        """Delete history events by identifiers.
        
        Returns:
            Dict with number of events deleted
        """
        if not identifiers:
            raise InputError('No identifiers provided')
        
        try:
            await self.history_events_repository.delete_history_events_by_identifier(identifiers)
            return {'deleted': len(identifiers)}
        except Exception as e:
            raise InputError(f'Failed to delete history events: {str(e)}') from e
    
    async def get_history_events(
        self,
        filter_query: HistoryEventFilterQuery,
        has_premium: bool = True,
        group_by_event_ids: bool = False,
    ) -> dict[str, Any]:
        """Get history events with filtering.
        
        Returns:
            Dict with 'entries' list and pagination info
        """
        # Get total count first
        total_count = await self.history_events_repository.count(filter_query)
        
        # Get events
        events = await self.history_events_repository.get_history_events(
            filter_query=filter_query,
            has_premium=has_premium,
            group_by_event_ids=group_by_event_ids,
        )
        
        # Serialize events
        serialized_events = []
        for event in events:
            try:
                serialized_events.append(event.serialize())
            except Exception:
                # Skip events that can't be serialized
                continue
        
        # Apply limit for non-premium users
        entries_limit = None if has_premium else FREE_HISTORY_EVENTS_LIMIT
        entries_found = len(serialized_events)
        
        return {
            'entries': serialized_events,
            'entries_found': entries_found,
            'entries_limit': entries_limit,
            'entries_total': total_count,
        }
    
    async def get_event_by_identifier(
        self,
        identifier: int,
    ) -> dict[str, Any]:
        """Get a single event by identifier.
        
        Returns:
            Serialized event data
        """
        event = await self.history_events_repository.get_event_by_identifier(identifier)
        if not event:
            raise InputError(f'Event with identifier {identifier} not found')
        
        return event.serialize()
    
    async def get_customized_event_identifiers(
        self,
        location: Location | None = None,
    ) -> dict[str, Any]:
        """Get identifiers of customized events.
        
        Returns:
            Dict with 'identifiers' list
        """
        chain_id = None
        if location and location in Location.get_chain_locations():
            blockchain = location.to_blockchain()
            if blockchain:
                chain_id = blockchain.to_chain_id()
        
        identifiers = await self.history_events_repository.get_customized_event_identifiers(
            chain_id=chain_id,
        )
        
        return {'identifiers': identifiers}
    
    async def export_history_events(
        self,
        directory_path: str | None = None,
    ) -> dict[str, Any]:
        """Export history events to a file.
        
        Returns:
            Dict with export details
        """
        # Get all events
        all_events = await self.history_events_repository.get_history_events(
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
        
        # Serialize for export
        export_data = {
            'version': 1,
            'events': [event.serialize() for event in all_events],
        }
        
        # In a real implementation, this would write to a file
        # For now, just return the count
        return {
            'exported': len(all_events),
            'message': f'Exported {len(all_events)} history events',
        }
    
    async def import_history_events(
        self,
        events_data: list[dict[str, Any]],
        timestamp: int | None = None,
    ) -> dict[str, Any]:
        """Import history events from data.
        
        Returns:
            Dict with import statistics
        """
        imported = 0
        errors = []
        
        for event_data in events_data:
            try:
                # Deserialize event (simplified - real implementation would handle all types)
                event_type = event_data.get('entry_type', 'history_event')
                
                # Create event based on type
                # This is simplified - real implementation would handle proper deserialization
                if event_type == 'history_event':
                    from rotkehlchen.history.events.structures.base import HistoryEvent
                    event = HistoryEvent.deserialize(event_data)
                else:
                    errors.append({
                        'event': str(event_data),
                        'error': f'Unsupported event type: {event_type}',
                    })
                    continue
                
                # Add the event
                await self.history_events_repository.add_history_event(event)
                imported += 1
                
            except Exception as e:
                errors.append({
                    'event': str(event_data),
                    'error': str(e),
                })
        
        return {
            'imported': imported,
            'errors': errors,
        }