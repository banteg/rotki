"""Repository for margin positions management"""


from sqlalchemy import select

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.orm.models import MarginPosition
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.exchanges.data_structures import MarginPosition as MarginPositionData
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp


class MarginPositionRepository(BaseRepository[MarginPosition]):
    """Repository for managing margin trading positions"""

    def __init__(self, session):
        super().__init__(session, MarginPosition)

    def add_margin_position(
        self,
        position_data: MarginPositionData,
    ) -> MarginPosition:
        """Add a new margin position"""
        position = MarginPosition(
            id=position_data.identifier,
            location=position_data.location.serialize_for_db(),
            open_time=int(position_data.open_time) if position_data.open_time else None,
            close_time=int(position_data.close_time) if position_data.close_time else None,
            profit_loss=str(position_data.profit_loss),
            pl_currency=position_data.pl_currency.identifier,
            fee=str(position_data.fee) if position_data.fee else None,
            fee_currency=position_data.fee_currency.identifier if position_data.fee_currency else None,
            link=position_data.link,
            notes=position_data.notes,
        )
        return self.add(position)

    def add_multiple_positions(
        self,
        positions: list[MarginPositionData],
    ) -> list[MarginPosition]:
        """Add multiple margin positions"""
        db_positions = []

        for pos_data in positions:
            position = MarginPosition(
                id=pos_data.identifier,
                location=pos_data.location.serialize_for_db(),
                open_time=int(pos_data.open_time) if pos_data.open_time else None,
                close_time=int(pos_data.close_time) if pos_data.close_time else None,
                profit_loss=str(pos_data.profit_loss),
                pl_currency=pos_data.pl_currency.identifier,
                fee=str(pos_data.fee) if pos_data.fee else None,
                fee_currency=pos_data.fee_currency.identifier if pos_data.fee_currency else None,
                link=pos_data.link,
                notes=pos_data.notes,
            )
            db_positions.append(position)

        return self.add_all(db_positions)

    def get_positions(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
        location: Location | None = None,
        only_open: bool = False,
        only_closed: bool = False,
    ) -> list[MarginPosition]:
        """Get margin positions with optional filters"""
        query = select(MarginPosition)

        if location is not None:
            query = query.filter_by(location=location.serialize_for_db())

        if from_timestamp is not None:
            query = query.filter(
                (MarginPosition.open_time >= int(from_timestamp)) |
                (MarginPosition.close_time >= int(from_timestamp)),
            )

        if to_timestamp is not None:
            query = query.filter(
                (MarginPosition.open_time <= int(to_timestamp)) |
                (MarginPosition.open_time.is_(None)),
            )

        if only_open:
            query = query.filter(MarginPosition.close_time.is_(None))
        elif only_closed:
            query = query.filter(MarginPosition.close_time.is_not(None))

        return list(self.session.execute(query).scalars().all())

    def get_position_by_id(self, position_id: str) -> MarginPosition | None:
        """Get a margin position by ID"""
        return self.get(id=position_id)

    def update_position(
        self,
        position_id: str,
        close_time: Timestamp | None = None,
        profit_loss: FVal | None = None,
        fee: FVal | None = None,
        notes: str | None = None,
    ) -> MarginPosition | None:
        """Update a margin position"""
        position = self.get_position_by_id(position_id)
        if not position:
            return None

        if close_time is not None:
            position.close_time = int(close_time)
        if profit_loss is not None:
            position.profit_loss = str(profit_loss)
        if fee is not None:
            position.fee = str(fee)
        if notes is not None:
            position.notes = notes

        return self.update(position)

    def delete_position(self, position_id: str) -> bool:
        """Delete a margin position"""
        return self.delete_by(id=position_id) > 0

    def to_domain_model(self, position: MarginPosition) -> MarginPositionData:
        """Convert database model to domain model"""
        return MarginPositionData(
            identifier=position.id,
            location=Location.deserialize_from_db(position.location),
            open_time=Timestamp(position.open_time) if position.open_time else None,
            close_time=Timestamp(position.close_time) if position.close_time else None,
            profit_loss=FVal(position.profit_loss) if position.profit_loss else FVal(0),
            pl_currency=Asset(position.pl_currency),
            fee=FVal(position.fee) if position.fee else None,
            fee_currency=Asset(position.fee_currency) if position.fee_currency else None,
            link=position.link,
            notes=position.notes,
        )

    def get_positions_count(
        self,
        location: Location | None = None,
    ) -> int:
        """Get count of margin positions"""
        if location:
            return self.count(location=location.serialize_for_db())
        return self.count()

    def get_total_profit_loss(
        self,
        location: Location | None = None,
        pl_currency: Asset | None = None,
    ) -> FVal:
        """Get total profit/loss across positions"""
        from sqlalchemy import func

        query = select(func.sum(MarginPosition.profit_loss))

        if location is not None:
            query = query.filter_by(location=location.serialize_for_db())
        if pl_currency is not None:
            query = query.filter_by(pl_currency=pl_currency.identifier)

        result = self.session.execute(query).scalar()
        return FVal(result) if result else FVal(0)
