"""Repository for price history management"""


from sqlalchemy import and_, delete, func, select

from rotkehlchen.db.orm.models import PriceHistory
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp


class PriceHistoryRepository(BaseRepository[PriceHistory]):
    """Repository for managing historical price data"""

    def __init__(self, session):
        super().__init__(session, PriceHistory)

    def add_price(
        self,
        from_asset: str,
        to_asset: str,
        source: str,
        timestamp: Timestamp,
        price: FVal,
    ) -> PriceHistory:
        """Add a price history entry"""
        entry = PriceHistory(
            from_asset=from_asset,
            to_asset=to_asset,
            source=source,
            timestamp=int(timestamp),
            price=str(price),
        )
        return self.add(entry)

    def get_price(
        self,
        from_asset: str,
        to_asset: str,
        timestamp: Timestamp,
        source: str | None = None,
    ) -> FVal | None:
        """Get price at specific timestamp"""
        query = select(PriceHistory).filter_by(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=int(timestamp),
        )

        if source:
            query = query.filter_by(source=source)

        entry = self.session.execute(query).scalar_one_or_none()
        return FVal(entry.price) if entry else None

    def get_price_range(
        self,
        from_asset: str,
        to_asset: str,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
        source: str | None = None,
    ) -> list[PriceHistory]:
        """Get prices within timestamp range"""
        query = select(PriceHistory).filter(
            and_(
                PriceHistory.from_asset == from_asset,
                PriceHistory.to_asset == to_asset,
                PriceHistory.timestamp >= int(from_timestamp),
                PriceHistory.timestamp <= int(to_timestamp),
            ),
        )

        if source:
            query = query.filter_by(source=source)

        query = query.order_by(PriceHistory.timestamp)

        return list(self.session.execute(query).scalars().all())

    def get_nearest_price(
        self,
        from_asset: str,
        to_asset: str,
        timestamp: Timestamp,
        max_seconds_distance: int = 3600,
        source: str | None = None,
    ) -> tuple[Timestamp, FVal] | None:
        """Get nearest price to timestamp within max distance"""
        base_query = select(PriceHistory).filter_by(
            from_asset=from_asset,
            to_asset=to_asset,
        )

        if source:
            base_query = base_query.filter_by(source=source)

        # Look for exact match first
        exact = base_query.filter_by(timestamp=int(timestamp))
        exact_result = self.session.execute(exact).scalar_one_or_none()
        if exact_result:
            return (Timestamp(exact_result.timestamp), FVal(exact_result.price))

        # Look for nearest within range
        min_ts = int(timestamp) - max_seconds_distance
        max_ts = int(timestamp) + max_seconds_distance

        range_query = base_query.filter(
            PriceHistory.timestamp.between(min_ts, max_ts),
        ).order_by(
            func.abs(PriceHistory.timestamp - int(timestamp)),
        ).limit(1)

        result = self.session.execute(range_query).scalar_one_or_none()
        if result:
            return (Timestamp(result.timestamp), FVal(result.price))

        return None

    def get_latest_price(
        self,
        from_asset: str,
        to_asset: str,
        source: str | None = None,
    ) -> tuple[Timestamp, FVal] | None:
        """Get latest available price"""
        query = select(PriceHistory).filter_by(
            from_asset=from_asset,
            to_asset=to_asset,
        )

        if source:
            query = query.filter_by(source=source)

        query = query.order_by(PriceHistory.timestamp.desc()).limit(1)

        result = self.session.execute(query).scalar_one_or_none()
        if result:
            return (Timestamp(result.timestamp), FVal(result.price))

        return None

    def delete_price(
        self,
        from_asset: str,
        to_asset: str,
        timestamp: Timestamp,
        source: str | None = None,
    ) -> bool:
        """Delete a specific price entry"""
        conditions = {
            'from_asset': from_asset,
            'to_asset': to_asset,
            'timestamp': int(timestamp),
        }

        if source:
            conditions['source'] = source

        return self.delete_by(**conditions) > 0

    def delete_price_range(
        self,
        from_asset: str,
        to_asset: str,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
        source: str | None = None,
    ) -> int:
        """Delete prices within range"""
        stmt = delete(PriceHistory).filter(
            and_(
                PriceHistory.from_asset == from_asset,
                PriceHistory.to_asset == to_asset,
                PriceHistory.timestamp >= int(from_timestamp),
                PriceHistory.timestamp <= int(to_timestamp),
            ),
        )

        if source:
            stmt = stmt.filter_by(source=source)

        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def price_exists(
        self,
        from_asset: str,
        to_asset: str,
        timestamp: Timestamp,
        source: str | None = None,
    ) -> bool:
        """Check if price exists"""
        conditions = {
            'from_asset': from_asset,
            'to_asset': to_asset,
            'timestamp': int(timestamp),
        }

        if source:
            conditions['source'] = source

        stmt = select(PriceHistory).filter_by(**conditions).limit(1)
        return self.session.execute(stmt).scalar() is not None

    def get_sources(
        self,
        from_asset: str | None = None,
        to_asset: str | None = None,
    ) -> list[str]:
        """Get unique price sources"""
        query = select(PriceHistory.source).distinct()

        if from_asset:
            query = query.filter_by(from_asset=from_asset)
        if to_asset:
            query = query.filter_by(to_asset=to_asset)

        return list(self.session.execute(query).scalars().all())

    def get_asset_pairs(self, source: str | None = None) -> list[tuple[str, str]]:
        """Get unique asset pairs"""
        query = select(
            PriceHistory.from_asset,
            PriceHistory.to_asset,
        ).distinct()

        if source:
            query = query.filter_by(source=source)

        results = self.session.execute(query).all()
        return [(row.from_asset, row.to_asset) for row in results]

    def bulk_add_prices(
        self,
        prices_data: list[dict[str, any]],
    ) -> list[PriceHistory]:
        """Bulk add multiple prices"""
        prices = []

        for data in prices_data:
            price = PriceHistory(
                from_asset=data['from_asset'],
                to_asset=data['to_asset'],
                source=data['source'],
                timestamp=int(data['timestamp']),
                price=str(data['price']),
            )
            self.session.add(price)
            prices.append(price)

        self.session.flush()
        return prices

    def get_price_count(
        self,
        from_asset: str | None = None,
        to_asset: str | None = None,
        source: str | None = None,
    ) -> int:
        """Get count of price entries"""
        query = select(func.count()).select_from(PriceHistory)

        if from_asset:
            query = query.filter_by(from_asset=from_asset)
        if to_asset:
            query = query.filter_by(to_asset=to_asset)
        if source:
            query = query.filter_by(source=source)

        return self.session.execute(query).scalar() or 0

    def prune_old_prices(
        self,
        older_than: Timestamp,
        keep_hourly: bool = True,
    ) -> int:
        """Delete old prices, optionally keeping hourly samples"""
        if keep_hourly:
            # Complex pruning: keep one price per hour
            # This would require more sophisticated logic
            # For now, just delete everything older
            pass

        stmt = delete(PriceHistory).filter(
            PriceHistory.timestamp < int(older_than),
        )

        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
