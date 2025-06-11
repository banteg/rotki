"""Repository for asset mappings management"""


from sqlalchemy import delete, select

from rotkehlchen.db.orm.global_db_models import (
    LocationAssetMapping,
    LocationUnsupportedAsset,
    MultiassetMapping,
)
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import Location


class AssetMappingRepository(BaseRepository[LocationAssetMapping]):
    """Repository for managing asset mappings across locations"""

    def __init__(self, session):
        super().__init__(session, LocationAssetMapping)

    # Location asset mappings

    def add_location_mapping(
        self,
        location: Location,
        location_symbol: str,
        asset: str,
    ) -> LocationAssetMapping:
        """Add a location asset mapping"""
        mapping = LocationAssetMapping(
            location=location.serialize_for_db(),
            location_symbol=location_symbol,
            asset=asset,
        )
        return self.add(mapping)

    def get_location_mapping(
        self,
        location: Location,
        location_symbol: str,
    ) -> LocationAssetMapping | None:
        """Get mapping for location and symbol"""
        return self.get(
            location=location.serialize_for_db(),
            location_symbol=location_symbol,
        )

    def get_asset_by_location_symbol(
        self,
        location: Location,
        location_symbol: str,
    ) -> str | None:
        """Get asset identifier for location symbol"""
        mapping = self.get_location_mapping(location, location_symbol)
        return mapping.asset if mapping else None

    def get_location_mappings(
        self,
        location: Location | None = None,
        asset: str | None = None,
    ) -> list[LocationAssetMapping]:
        """Get location mappings with filters"""
        query = select(LocationAssetMapping)

        if location:
            query = query.filter_by(location=location.serialize_for_db())
        if asset:
            query = query.filter_by(asset=asset)

        return list(self.session.execute(query).scalars().all())

    def delete_location_mapping(
        self,
        location: Location,
        location_symbol: str,
    ) -> bool:
        """Delete a location mapping"""
        return self.delete_by(
            location=location.serialize_for_db(),
            location_symbol=location_symbol,
        ) > 0

    # Unsupported assets

    def add_unsupported_asset(
        self,
        location: Location,
        location_symbol: str,
    ) -> LocationUnsupportedAsset:
        """Mark an asset as unsupported at location"""
        unsupported = LocationUnsupportedAsset(
            location=location.serialize_for_db(),
            location_symbol=location_symbol,
        )
        self.session.add(unsupported)
        self.session.flush()
        return unsupported

    def is_asset_unsupported(
        self,
        location: Location,
        location_symbol: str,
    ) -> bool:
        """Check if asset is unsupported at location"""
        stmt = select(LocationUnsupportedAsset).filter_by(
            location=location.serialize_for_db(),
            location_symbol=location_symbol,
        ).limit(1)
        return self.session.execute(stmt).scalar() is not None

    def get_unsupported_assets(
        self,
        location: Location | None = None,
    ) -> list[LocationUnsupportedAsset]:
        """Get unsupported assets"""
        if location:
            stmt = select(LocationUnsupportedAsset).filter_by(
                location=location.serialize_for_db(),
            )
        else:
            stmt = select(LocationUnsupportedAsset)

        return list(self.session.execute(stmt).scalars().all())

    def delete_unsupported_asset(
        self,
        location: Location,
        location_symbol: str,
    ) -> bool:
        """Remove unsupported asset marking"""
        stmt = delete(LocationUnsupportedAsset).filter_by(
            location=location.serialize_for_db(),
            location_symbol=location_symbol,
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount > 0

    # Multi-asset mappings

    def add_multiasset_mapping(
        self,
        from_asset: str,
        to_asset: str,
        fraction: str,
    ) -> MultiassetMapping:
        """Add a multi-asset mapping"""
        mapping = MultiassetMapping(
            from_asset=from_asset,
            to_asset=to_asset,
            fraction=fraction,
        )
        self.session.add(mapping)
        self.session.flush()
        return mapping

    def get_multiasset_mappings(
        self,
        from_asset: str | None = None,
        to_asset: str | None = None,
    ) -> list[MultiassetMapping]:
        """Get multi-asset mappings"""
        query = select(MultiassetMapping)

        if from_asset:
            query = query.filter_by(from_asset=from_asset)
        if to_asset:
            query = query.filter_by(to_asset=to_asset)

        return list(self.session.execute(query).scalars().all())

    def delete_multiasset_mapping(
        self,
        from_asset: str,
        to_asset: str,
    ) -> bool:
        """Delete a multi-asset mapping"""
        stmt = delete(MultiassetMapping).filter_by(
            from_asset=from_asset,
            to_asset=to_asset,
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount > 0

    def get_asset_conversions(self, from_asset: str) -> list[tuple[str, str]]:
        """Get all conversion targets for an asset with fractions"""
        mappings = self.get_multiasset_mappings(from_asset=from_asset)
        return [(m.to_asset, m.fraction) for m in mappings]

    def bulk_add_location_mappings(
        self,
        mappings_data: list[dict[str, any]],
    ) -> list[LocationAssetMapping]:
        """Bulk add location mappings"""
        mappings = []

        for data in mappings_data:
            mapping = LocationAssetMapping(
                location=data['location'].serialize_for_db(),
                location_symbol=data['location_symbol'],
                asset=data['asset'],
            )
            self.session.add(mapping)
            mappings.append(mapping)

        self.session.flush()
        return mappings

    def get_location_symbols_for_asset(
        self,
        asset: str,
    ) -> dict[Location, list[str]]:
        """Get all location symbols that map to an asset"""
        mappings = self.get_location_mappings(asset=asset)
        result = {}

        for mapping in mappings:
            location = Location.deserialize_from_db(mapping.location)
            if location not in result:
                result[location] = []
            result[location].append(mapping.location_symbol)

        return result
