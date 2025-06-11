"""Repository for Cowswap order management"""


from sqlalchemy import func, select

from rotkehlchen.db.orm.models import CowswapOrder
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp


class CowswapRepository(BaseRepository[CowswapOrder]):
    """Repository for managing Cowswap orders"""

    def __init__(self, session):
        super().__init__(session, CowswapOrder)

    def add_order(
        self,
        order_uid: str,
        timestamp: Timestamp,
        from_asset: str,
        to_asset: str,
        amount: FVal,
        fee_amount: FVal,
    ) -> CowswapOrder:
        """Add a Cowswap order"""
        order = CowswapOrder(
            order_uid=order_uid,
            timestamp=int(timestamp),
            from_asset=from_asset,
            to_asset=to_asset,
            amount=str(amount),
            fee_amount=str(fee_amount),
        )
        return self.add(order)

    def get_order(self, order_uid: str) -> CowswapOrder | None:
        """Get an order by UID"""
        return self.get(order_uid=order_uid)

    def get_orders(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
        from_asset: str | None = None,
        to_asset: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[CowswapOrder]:
        """Get orders with filters"""
        query = select(CowswapOrder)

        if from_timestamp is not None:
            query = query.filter(CowswapOrder.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(CowswapOrder.timestamp <= int(to_timestamp))

        if from_asset:
            query = query.filter_by(from_asset=from_asset)

        if to_asset:
            query = query.filter_by(to_asset=to_asset)

        # Order by timestamp descending
        query = query.order_by(CowswapOrder.timestamp.desc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def delete_order(self, order_uid: str) -> bool:
        """Delete an order"""
        return self.delete_by(order_uid=order_uid) > 0

    def order_exists(self, order_uid: str) -> bool:
        """Check if an order exists"""
        return self.get_order(order_uid) is not None

    def get_orders_by_asset_pair(
        self,
        from_asset: str,
        to_asset: str,
    ) -> list[CowswapOrder]:
        """Get all orders for a specific asset pair"""
        stmt = select(CowswapOrder).filter_by(
            from_asset=from_asset,
            to_asset=to_asset,
        ).order_by(CowswapOrder.timestamp.desc())

        return list(self.session.execute(stmt).scalars().all())

    def get_total_volume(
        self,
        from_asset: str | None = None,
        to_asset: str | None = None,
    ) -> FVal:
        """Get total trading volume"""
        query = select(func.sum(CowswapOrder.amount))

        if from_asset:
            query = query.filter_by(from_asset=from_asset)
        if to_asset:
            query = query.filter_by(to_asset=to_asset)

        result = self.session.execute(query).scalar()
        return FVal(result) if result else FVal(0)

    def get_total_fees(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
    ) -> FVal:
        """Get total fees paid"""
        query = select(func.sum(CowswapOrder.fee_amount))

        if from_timestamp is not None:
            query = query.filter(CowswapOrder.timestamp >= int(from_timestamp))

        if to_timestamp is not None:
            query = query.filter(CowswapOrder.timestamp <= int(to_timestamp))

        result = self.session.execute(query).scalar()
        return FVal(result) if result else FVal(0)

    def get_orders_count(
        self,
        from_asset: str | None = None,
        to_asset: str | None = None,
    ) -> int:
        """Get count of orders"""
        query = select(func.count()).select_from(CowswapOrder)

        if from_asset:
            query = query.filter_by(from_asset=from_asset)
        if to_asset:
            query = query.filter_by(to_asset=to_asset)

        return self.session.execute(query).scalar() or 0

    def get_latest_order(self) -> CowswapOrder | None:
        """Get the most recent order"""
        stmt = select(CowswapOrder).order_by(
            CowswapOrder.timestamp.desc(),
        ).limit(1)

        return self.session.execute(stmt).scalar_one_or_none()

    def get_unique_assets(self) -> dict[str, set[str]]:
        """Get unique from and to assets"""
        from_assets_stmt = select(CowswapOrder.from_asset).distinct()
        to_assets_stmt = select(CowswapOrder.to_asset).distinct()

        from_assets = set(self.session.execute(from_assets_stmt).scalars().all())
        to_assets = set(self.session.execute(to_assets_stmt).scalars().all())

        return {
            'from_assets': from_assets,
            'to_assets': to_assets,
        }

    def bulk_add_orders(
        self,
        orders_data: list[dict[str, any]],
    ) -> list[CowswapOrder]:
        """Bulk add multiple orders"""
        orders = []

        for data in orders_data:
            order = CowswapOrder(
                order_uid=data['order_uid'],
                timestamp=int(data['timestamp']),
                from_asset=data['from_asset'],
                to_asset=data['to_asset'],
                amount=str(data['amount']),
                fee_amount=str(data['fee_amount']),
            )
            self.session.add(order)
            orders.append(order)

        self.session.flush()
        return orders
