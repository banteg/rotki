"""Repository for location-specific data management"""


from sqlalchemy import select

from rotkehlchen.db.orm.models import LocationData
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import Location


class LocationDataRepository(BaseRepository[LocationData]):
    """Repository for managing location-specific data"""

    def __init__(self, session):
        super().__init__(session, LocationData)

    def set_data(
        self,
        location: Location,
        data_type: str,
        data: str,
    ) -> LocationData:
        """Set or update location data"""
        # Check if entry exists
        location_data = self.get_data(location, data_type)

        if location_data:
            location_data.data = data
            return self.update(location_data)
        else:
            location_data = LocationData(
                location=location.serialize_for_db(),
                data_type=data_type,
                data=data,
            )
            return self.add(location_data)

    def get_data(
        self,
        location: Location,
        data_type: str,
    ) -> LocationData | None:
        """Get location data"""
        return self.get(
            location=location.serialize_for_db(),
            data_type=data_type,
        )

    def get_all_data(
        self,
        location: Location | None = None,
        data_type: str | None = None,
    ) -> list[LocationData]:
        """Get all location data with optional filters"""
        query = select(LocationData)

        if location:
            query = query.filter_by(location=location.serialize_for_db())

        if data_type:
            query = query.filter_by(data_type=data_type)

        return list(self.session.execute(query).scalars().all())

    def delete_data(
        self,
        location: Location,
        data_type: str,
    ) -> bool:
        """Delete location data"""
        return self.delete_by(
            location=location.serialize_for_db(),
            data_type=data_type,
        ) > 0

    def delete_all_location_data(self, location: Location) -> int:
        """Delete all data for a location"""
        return self.delete_by(location=location.serialize_for_db())

    def data_exists(
        self,
        location: Location,
        data_type: str,
    ) -> bool:
        """Check if location data exists"""
        return self.get_data(location, data_type) is not None

    def get_locations_with_data(self, data_type: str) -> list[Location]:
        """Get all locations that have data of a specific type"""
        stmt = select(LocationData.location).filter_by(
            data_type=data_type,
        ).distinct()

        location_chars = self.session.execute(stmt).scalars().all()
        return [Location.deserialize_from_db(char) for char in location_chars]

    def get_data_types_for_location(self, location: Location) -> list[str]:
        """Get all data types available for a location"""
        stmt = select(LocationData.data_type).filter_by(
            location=location.serialize_for_db(),
        ).distinct()

        return list(self.session.execute(stmt).scalars().all())

    def bulk_set_data(
        self,
        updates: list[dict[str, any]],
    ) -> list[LocationData]:
        """Bulk set location data"""
        results = []

        for update in updates:
            location_data = self.set_data(
                location=update['location'],
                data_type=update['data_type'],
                data=update['data'],
            )
            results.append(location_data)

        return results

    def copy_location_data(
        self,
        from_location: Location,
        to_location: Location,
        data_type: str | None = None,
    ) -> int:
        """Copy data from one location to another"""
        query = select(LocationData).filter_by(
            location=from_location.serialize_for_db(),
        )

        if data_type:
            query = query.filter_by(data_type=data_type)

        source_data = self.session.execute(query).scalars().all()
        copied_count = 0

        for data in source_data:
            self.set_data(
                location=to_location,
                data_type=data.data_type,
                data=data.data,
            )
            copied_count += 1

        return copied_count

    def search_data(
        self,
        search_term: str,
        location: Location | None = None,
        data_type: str | None = None,
    ) -> list[LocationData]:
        """Search for data containing a term"""
        query = select(LocationData).filter(
            LocationData.data.like(f'%{search_term}%'),
        )

        if location:
            query = query.filter_by(location=location.serialize_for_db())

        if data_type:
            query = query.filter_by(data_type=data_type)

        return list(self.session.execute(query).scalars().all())
