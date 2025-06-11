"""Repository for ETH2 validator management"""


from sqlalchemy import func, select

from rotkehlchen.db.orm.models import ETH2Validator
from rotkehlchen.db.orm.repositories.base import BaseRepository


class ETH2ValidatorRepository(BaseRepository[ETH2Validator]):
    """Repository for managing ETH2 validators"""

    def __init__(self, session):
        super().__init__(session, ETH2Validator)

    def add_validator(
        self,
        validator_index: int,
        public_key: str,
        ownership_percentage: float = 100.0,
    ) -> ETH2Validator:
        """Add an ETH2 validator"""
        validator = ETH2Validator(
            validator_index=validator_index,
            public_key=public_key,
            ownership_percentage=str(ownership_percentage),
        )
        return self.add(validator)

    def get_validator(self, validator_index: int) -> ETH2Validator | None:
        """Get a validator by index"""
        return self.get(validator_index=validator_index)

    def get_validator_by_public_key(self, public_key: str) -> ETH2Validator | None:
        """Get a validator by public key"""
        return self.get(public_key=public_key)

    def get_all_validators(
        self,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ETH2Validator]:
        """Get all validators"""
        query = select(ETH2Validator).order_by(ETH2Validator.validator_index)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def update_validator_ownership(
        self,
        validator_index: int,
        ownership_percentage: float,
    ) -> ETH2Validator | None:
        """Update validator ownership percentage"""
        validator = self.get_validator(validator_index)
        if not validator:
            return None

        validator.ownership_percentage = str(ownership_percentage)
        return self.update(validator)

    def delete_validator(self, validator_index: int) -> bool:
        """Delete a validator"""
        return self.delete_by(validator_index=validator_index) > 0

    def validator_exists(self, validator_index: int) -> bool:
        """Check if a validator exists"""
        return self.get_validator(validator_index) is not None

    def get_validators_by_indices(
        self,
        indices: list[int],
    ) -> list[ETH2Validator]:
        """Get multiple validators by their indices"""
        if not indices:
            return []

        stmt = select(ETH2Validator).filter(
            ETH2Validator.validator_index.in_(indices),
        ).order_by(ETH2Validator.validator_index)

        return list(self.session.execute(stmt).scalars().all())

    def get_validators_count(self) -> int:
        """Get total count of validators"""
        query = select(func.count()).select_from(ETH2Validator)
        return self.session.execute(query).scalar() or 0

    def get_owned_validators(
        self,
        min_ownership: float = 0.0,
    ) -> list[ETH2Validator]:
        """Get validators with ownership above threshold"""
        stmt = select(ETH2Validator).filter(
            ETH2Validator.ownership_percentage > str(min_ownership),
        ).order_by(ETH2Validator.validator_index)

        return list(self.session.execute(stmt).scalars().all())

    def bulk_add_validators(
        self,
        validators_data: list[dict[str, any]],
    ) -> list[ETH2Validator]:
        """Bulk add multiple validators"""
        validators = []

        for data in validators_data:
            validator = ETH2Validator(
                validator_index=data['validator_index'],
                public_key=data['public_key'],
                ownership_percentage=str(data.get('ownership_percentage', 100.0)),
            )
            self.session.add(validator)
            validators.append(validator)

        self.session.flush()
        return validators

    def get_validators_by_ownership_range(
        self,
        min_ownership: float,
        max_ownership: float,
    ) -> list[ETH2Validator]:
        """Get validators within ownership percentage range"""
        stmt = select(ETH2Validator).filter(
            ETH2Validator.ownership_percentage.between(
                str(min_ownership),
                str(max_ownership),
            ),
        ).order_by(ETH2Validator.validator_index)

        return list(self.session.execute(stmt).scalars().all())
