"""Repository for asset updates management"""


from sqlalchemy import and_, delete, func, select

from rotkehlchen.db.orm.models import AssetUpdate
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import Timestamp


class AssetUpdateRepository(BaseRepository[AssetUpdate]):
    """Repository for managing asset update records"""

    def __init__(self, session):
        super().__init__(session, AssetUpdate)

    def add_update(
        self,
        asset_id: str,
        update_type: str,
        timestamp: Timestamp,
        data: str | None = None,
    ) -> AssetUpdate:
        """Add an asset update record"""
        update = AssetUpdate(
            asset_id=asset_id,
            update_type=update_type,
            timestamp=int(timestamp),
            data=data,
        )
        return self.add(update)

    def get_updates(
        self,
        asset_id: str | None = None,
        update_type: str | None = None,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AssetUpdate]:
        """Get asset updates with filters"""
        query = select(AssetUpdate)

        if asset_id:
            query = query.filter_by(asset_id=asset_id)

        if update_type:
            query = query.filter_by(update_type=update_type)

        if from_timestamp is not None:
            query = query.filter(AssetUpdate.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(AssetUpdate.timestamp <= int(to_timestamp))

        # Order by timestamp descending
        query = query.order_by(AssetUpdate.timestamp.desc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def get_latest_update(
        self,
        asset_id: str,
        update_type: str | None = None,
    ) -> AssetUpdate | None:
        """Get the latest update for an asset"""
        query = select(AssetUpdate).filter_by(asset_id=asset_id)

        if update_type:
            query = query.filter_by(update_type=update_type)

        query = query.order_by(AssetUpdate.timestamp.desc()).limit(1)

        return self.session.execute(query).scalar_one_or_none()

    def delete_updates(
        self,
        asset_id: str,
        update_type: str | None = None,
        before_timestamp: Timestamp | None = None,
    ) -> int:
        """Delete asset updates"""
        stmt = delete(AssetUpdate).filter_by(asset_id=asset_id)

        if update_type:
            stmt = stmt.filter_by(update_type=update_type)

        if before_timestamp is not None:
            stmt = stmt.filter(AssetUpdate.timestamp < int(before_timestamp))

        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def update_exists(
        self,
        asset_id: str,
        update_type: str,
        timestamp: Timestamp,
    ) -> bool:
        """Check if a specific update exists"""
        stmt = select(AssetUpdate).filter_by(
            asset_id=asset_id,
            update_type=update_type,
            timestamp=int(timestamp),
        ).limit(1)
        return self.session.execute(stmt).scalar() is not None

    def get_assets_needing_update(
        self,
        update_type: str,
        older_than: Timestamp,
    ) -> list[str]:
        """Get assets that haven't been updated recently"""
        # Get all assets with their latest update
        subquery = (
            select(
                AssetUpdate.asset_id,
                func.max(AssetUpdate.timestamp).label('latest_timestamp'),
            )
            .filter_by(update_type=update_type)
            .group_by(AssetUpdate.asset_id)
            .subquery()
        )

        # Filter for assets with old updates
        stmt = (
            select(subquery.c.asset_id)
            .filter(subquery.c.latest_timestamp < int(older_than))
        )

        return list(self.session.execute(stmt).scalars().all())

    def get_update_types(self) -> list[str]:
        """Get all unique update types"""
        stmt = select(AssetUpdate.update_type).distinct()
        return list(self.session.execute(stmt).scalars().all())

    def get_updates_count(
        self,
        asset_id: str | None = None,
        update_type: str | None = None,
    ) -> int:
        """Get count of updates"""
        query = select(func.count()).select_from(AssetUpdate)

        if asset_id:
            query = query.filter_by(asset_id=asset_id)
        if update_type:
            query = query.filter_by(update_type=update_type)

        return self.session.execute(query).scalar() or 0

    def bulk_add_updates(
        self,
        updates_data: list[dict[str, any]],
    ) -> list[AssetUpdate]:
        """Bulk add multiple updates"""
        updates = []

        for data in updates_data:
            update = AssetUpdate(
                asset_id=data['asset_id'],
                update_type=data['update_type'],
                timestamp=int(data['timestamp']),
                data=data.get('data'),
            )
            self.session.add(update)
            updates.append(update)

        self.session.flush()
        return updates

    def get_update_history(
        self,
        asset_id: str,
        update_type: str,
    ) -> list[AssetUpdate]:
        """Get full update history for an asset and type"""
        stmt = select(AssetUpdate).filter_by(
            asset_id=asset_id,
            update_type=update_type,
        ).order_by(AssetUpdate.timestamp.desc())

        return list(self.session.execute(stmt).scalars().all())

    def prune_old_updates(
        self,
        older_than: Timestamp,
        keep_latest: bool = True,
    ) -> int:
        """Delete old updates, optionally keeping the latest for each asset"""
        if keep_latest:
            # Get latest update for each asset/type combination
            latest_subquery = (
                select(
                    AssetUpdate.asset_id,
                    AssetUpdate.update_type,
                    func.max(AssetUpdate.identifier).label('latest_id'),
                )
                .group_by(AssetUpdate.asset_id, AssetUpdate.update_type)
                .subquery()
            )

            # Delete all except the latest
            stmt = delete(AssetUpdate).filter(
                and_(
                    AssetUpdate.timestamp < int(older_than),
                    AssetUpdate.identifier.notin_(
                        select(latest_subquery.c.latest_id),
                    ),
                ),
            )
        else:
            # Delete all older than timestamp
            stmt = delete(AssetUpdate).filter(
                AssetUpdate.timestamp < int(older_than),
            )

        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
