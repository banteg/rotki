"""Repository for used query ranges management"""


from rotkehlchen.db.orm.models import UsedQueryRange
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import Timestamp


class QueryRangeRepository(BaseRepository[UsedQueryRange]):
    """Repository for managing query ranges for various data sources"""

    def __init__(self, session):
        super().__init__(session, UsedQueryRange)

    def get_range(self, name: str) -> tuple[Timestamp, Timestamp] | None:
        """Get query range for a specific name"""
        query_range = self.get(name=name)
        if not query_range:
            return None

        start = Timestamp(query_range.start_ts) if query_range.start_ts else Timestamp(0)
        end = Timestamp(query_range.end_ts) if query_range.end_ts else Timestamp(0)

        return (start, end) if start or end else None

    def update_range(
        self,
        name: str,
        start_ts: Timestamp | None = None,
        end_ts: Timestamp | None = None,
    ) -> UsedQueryRange:
        """Update or create a query range"""
        query_range = self.get(name=name)

        if query_range:
            # Update existing
            if start_ts is not None:
                query_range.start_ts = int(start_ts)
            if end_ts is not None:
                query_range.end_ts = int(end_ts)
            return self.update(query_range)
        else:
            # Create new
            query_range = UsedQueryRange(
                name=name,
                start_ts=int(start_ts) if start_ts else None,
                end_ts=int(end_ts) if end_ts else None,
            )
            return self.add(query_range)

    def update_used_query_range(
        self,
        name: str,
        start_ts: Timestamp,
        end_ts: Timestamp,
        ranges_to_query: list[tuple[Timestamp, Timestamp]] | None = None,
    ) -> None:
        """
        Update query range, merging with existing range if needed.
        This maintains the full range of data that has been queried.
        """
        existing_range = self.get_range(name)

        if existing_range:
            # Merge with existing range
            existing_start, existing_end = existing_range
            new_start = min(start_ts, existing_start) if existing_start else start_ts
            new_end = max(end_ts, existing_end) if existing_end else end_ts
        else:
            new_start = start_ts
            new_end = end_ts

        self.update_range(name, new_start, new_end)

    def delete_range(self, name: str) -> bool:
        """Delete a query range"""
        return self.delete_by(name=name) > 0

    def get_all_ranges(self) -> dict[str, tuple[Timestamp, Timestamp]]:
        """Get all query ranges"""
        ranges = self.get_all()
        result = {}

        for query_range in ranges:
            if query_range.start_ts or query_range.end_ts:
                start = Timestamp(query_range.start_ts) if query_range.start_ts else Timestamp(0)
                end = Timestamp(query_range.end_ts) if query_range.end_ts else Timestamp(0)
                result[query_range.name] = (start, end)

        return result

    def reset_range(self, name: str) -> None:
        """Reset a query range to unqueried state"""
        query_range = self.get(name=name)
        if query_range:
            query_range.start_ts = None
            query_range.end_ts = None
            self.update(query_range)

    def has_queried_range(self, name: str) -> bool:
        """Check if a range has been queried"""
        query_range = self.get(name=name)
        return bool(query_range and (query_range.start_ts or query_range.end_ts))

    def get_last_query_timestamp(
        self,
        name: str,
        position: str = 'end',
    ) -> Timestamp | None:
        """Get the last timestamp that was queried"""
        query_range = self.get(name=name)
        if not query_range:
            return None

        if position == 'start':
            return Timestamp(query_range.start_ts) if query_range.start_ts else None
        else:  # position == 'end'
            return Timestamp(query_range.end_ts) if query_range.end_ts else None
