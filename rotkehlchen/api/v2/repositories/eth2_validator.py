"""Repository for managing ETH2 validators."""
from typing import TYPE_CHECKING, Optional

from sqlmodel import func, select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.user.staking import Eth2DailyStakingDetails, Eth2Validator

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress, Timestamp


class Eth2ValidatorRepository(BaseRepository[Eth2Validator]):
    """Repository for managing ETH2 validators."""

    model = Eth2Validator

    def get_validators_by_owner(
        self,
        owner_address: Optional['ChecksumEvmAddress'] = None,
    ) -> list[Eth2Validator]:
        """Get all validators, optionally filtered by owner address."""
        query = select(self.model)

        if owner_address is not None:
            query = query.where(self.model.withdrawal_address == owner_address)

        result = self.session.exec(query)
        return list(result.all())

    def get_validator_by_index(
        self,
        validator_index: int,
    ) -> Eth2Validator | None:
        """Get a validator by its index."""
        query = select(self.model).where(self.model.validator_index == validator_index)
        result = self.session.exec(query).first()
        return result

    def get_validator_by_pubkey(
        self,
        pubkey: str,
    ) -> Eth2Validator | None:
        """Get a validator by its public key."""
        query = select(self.model).where(self.model.public_key == pubkey)
        result = self.session.exec(query).first()
        return result

    def add_validator(
        self,
        validator_index: int,
        public_key: str,
        withdrawal_address: Optional['ChecksumEvmAddress'] = None,
        activation_timestamp: Optional['Timestamp'] = None,
    ) -> Eth2Validator:
        """Add a new ETH2 validator."""
        validator_data = {
            'validator_index': validator_index,
            'public_key': public_key,
            'withdrawal_address': withdrawal_address,
            'activation_timestamp': activation_timestamp,
        }
        return self.create(validator_data)

    def remove_validator(
        self,
        validator_index: int,
    ) -> bool:
        """Remove a validator by its index."""
        validator = self.get_validator_by_index(validator_index)

        if validator:
            self.session.delete(validator)
            self.session.commit()
            return True
        return False

    def count_validators_by_owner(
        self,
        owner_address: 'ChecksumEvmAddress',
    ) -> int:
        """Count the number of validators owned by an address."""
        query = select(func.count(self.model.identifier)).where(
            self.model.withdrawal_address == owner_address,
        )
        result = self.session.exec(query).one()
        return result

    def get_active_validators(
        self,
        owner_address: Optional['ChecksumEvmAddress'] = None,
    ) -> list[Eth2Validator]:
        """Get validators that are currently active."""
        query = select(self.model).where(
            self.model.activation_timestamp.is_not(None),
            self.model.activation_timestamp <= func.now(),
        )

        if owner_address is not None:
            query = query.where(self.model.withdrawal_address == owner_address)

        result = self.session.exec(query)
        return list(result.all())

    def get_daily_staking_details(
        self,
        validator_index: int,
        from_timestamp: Optional['Timestamp'] = None,
        to_timestamp: Optional['Timestamp'] = None,
    ) -> list[Eth2DailyStakingDetails]:
        """Get daily staking details for a validator."""
        query = select(Eth2DailyStakingDetails).where(
            Eth2DailyStakingDetails.validator_index == validator_index,
        )

        if from_timestamp is not None:
            query = query.where(Eth2DailyStakingDetails.timestamp >= from_timestamp)

        if to_timestamp is not None:
            query = query.where(Eth2DailyStakingDetails.timestamp <= to_timestamp)

        query = query.order_by(Eth2DailyStakingDetails.timestamp.desc())

        result = self.session.exec(query)
        return list(result.all())

    def add_daily_staking_details(
        self,
        validator_index: int,
        timestamp: 'Timestamp',
        details: dict,
    ) -> Eth2DailyStakingDetails:
        """Add daily staking details for a validator."""
        staking_data = {
            'validator_index': validator_index,
            'timestamp': timestamp,
            **details,
        }
        staking_detail = Eth2DailyStakingDetails(**staking_data)
        self.session.add(staking_detail)
        self.session.commit()
        return staking_detail

    def get_total_staking_rewards(
        self,
        owner_address: 'ChecksumEvmAddress',
        from_timestamp: Optional['Timestamp'] = None,
    ) -> dict:
        """Get total staking rewards for all validators owned by an address."""
        # Get validators owned by the address
        validators = self.get_validators_by_owner(owner_address)
        validator_indices = [v.validator_index for v in validators]

        if not validator_indices:
            return {'total_consensus_rewards': 0, 'total_execution_rewards': 0}

        # Query for sum of rewards
        query = select(
            func.sum(Eth2DailyStakingDetails.consensus_rewards).label('total_consensus'),
            func.sum(Eth2DailyStakingDetails.execution_rewards).label('total_execution'),
        ).where(Eth2DailyStakingDetails.validator_index.in_(validator_indices))

        if from_timestamp is not None:
            query = query.where(Eth2DailyStakingDetails.timestamp >= from_timestamp)

        result = self.session.exec(query).one()

        return {
            'total_consensus_rewards': result.total_consensus or 0,
            'total_execution_rewards': result.total_execution or 0,
            'total_rewards': (result.total_consensus or 0) + (result.total_execution or 0),
        }
