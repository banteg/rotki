"""Async Eth2 repository for v2 API.

Handles all ETH2/staking related async database operations.
"""
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select as sqlmodel_select

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    ValidatorDailyStats,
    ValidatorDetails,
    ValidatorDetailsWithStatus,
)
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS, HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.filtering import (
    Eth2DailyStatsFilterQuery,
    EthStakingEventFilterQuery,
    EthWithdrawalFilterQuery,
    HistoryEventFilterQuery,
)
from rotki2.db.models.user.history import HistoryEvent
from rotki2.db.models.user.staking import Eth2DailyStakingDetails, Eth2Validator, EthStakingEventInfo
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Collection


class AsyncEth2Repository:
    """Async repository for ETH2/staking data.
    
    Note: This doesn't inherit from AsyncBaseRepository as ETH2 data
    uses multiple custom tables that don't map to a single model.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_validators_to_query_for_stats(
        self,
        up_to_ts: Timestamp,
    ) -> list[tuple[int, Timestamp, Timestamp | None]]:
        """Gets a list of validators that need to be queried for new daily stats
        
        Validators need to be queried if last time they are queried was more than 2 days.
        
        Returns a list of tuples. First entry is validator index, second entry is
        last queried timestamp for daily stats of that validator and third one is
        an optional timestamp of the validator's exit.
        """
        # Note: This query is too complex for ORM - uses subqueries, UNION, and complex joins
        # Keeping raw SQL for performance and maintainability
        query_str = """
            SELECT D.validator_index, D.timestamp FROM eth2_validators V LEFT JOIN
            eth2_daily_staking_details D ON
            V.validator_index = D.validator_index AND :up_to_ts - (SELECT MAX(timestamp) FROM eth2_daily_staking_details WHERE validator_index=V.validator_index) > :time_threshold WHERE D.validator_index IS NOT NULL AND D.timestamp==(SELECT MAX(timestamp) FROM eth2_daily_staking_details WHERE validator_index=V.validator_index)
            UNION
            SELECT DISTINCT V2.validator_index, 0 FROM eth2_validators V2 WHERE
            V2.validator_index NOT IN (SELECT validator_index FROM eth2_daily_staking_details)
        """
        
        result = await self.session.execute(
            text(query_str),
            {
                'up_to_ts': up_to_ts,
                'time_threshold': DAY_IN_SECONDS * 2 + HOUR_IN_SECONDS * 18,
            }
        )
        stats_data = result.fetchall()
        
        # Get exit data - keep raw SQL due to join complexity
        exit_result = await self.session.execute(
            text("""
                SELECT S.validator_index, H.timestamp FROM eth_staking_events_info S
                LEFT JOIN history_events H ON S.identifier=H.identifier
                WHERE S.is_exit_or_blocknumber=1
            """)
        )
        exited_data = {row[0]: ts_ms_to_sec(row[1]) for row in exit_result}
        
        # Build result
        results = []
        for data in stats_data:
            exit_ts = exited_data.get(data[0])
            if exit_ts is not None and exit_ts <= data[1]:
                # skip query for validators that exited and last stats is around exit
                continue
            results.append((data[0], data[1], exit_ts))
        
        return results
    
    async def add_validator_daily_stats(self, stats: list[ValidatorDailyStats]) -> None:
        """Adds given daily stats for validator in the DB. If an entry exists it's skipped"""
        for entry in stats:
            # Check if entry already exists
            statement = sqlmodel_select(Eth2DailyStakingDetails).where(
                Eth2DailyStakingDetails.validator_index == entry.validator_index,
                Eth2DailyStakingDetails.timestamp == entry.timestamp,
            )
            result = await self.session.execute(statement)
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Add new entry
                new_stat = Eth2DailyStakingDetails(
                    validator_index=entry.validator_index,
                    timestamp=entry.timestamp,
                    pnl=str(entry.pnl),
                )
                self.session.add(new_stat)
        
        await self.session.commit()
    
    async def get_validator_daily_stats_and_limit_info(
        self,
        filter_query: Eth2DailyStatsFilterQuery,
    ) -> tuple[list[ValidatorDailyStats], int, FVal]:
        """Gets all eth2 daily stats for the query from the DB
        
        Returns a tuple with the following in order:
         - A list of the daily stats
         - How many are the total entries found for the filter (ignoring pagination)
         - Sum of ETH gained/lost for the filter
        """
        stats = await self.get_validator_daily_stats(filter_query=filter_query)
        
        # Get count and sum
        # Note: Dynamic filter queries require raw SQL
        query, bindings = filter_query.prepare(with_pagination=False)
        count_query = f'SELECT COUNT(*), SUM(pnl) FROM (SELECT * FROM eth2_daily_staking_details {query})'
        
        result = await self.session.execute(text(count_query), bindings)
        row = result.fetchone()
        count = row[0] if row else 0
        eth_sum = FVal(row[1]) if row and row[1] is not None else ZERO
        
        return stats, count, eth_sum
    
    async def get_validator_daily_stats(
        self,
        filter_query: Eth2DailyStatsFilterQuery | None = None,
        validator_indices: list[int] | None = None,
    ) -> list[ValidatorDailyStats]:
        """Gets daily stats for validators based on filter"""
        if filter_query is not None:
            # Note: Dynamic filter queries require raw SQL
            query_str, bindings = filter_query.prepare()
            query = f'SELECT * FROM eth2_daily_staking_details {query_str}'
            result = await self.session.execute(text(query), bindings)
            return [
                ValidatorDailyStats(
                    validator_index=row[0],
                    timestamp=Timestamp(row[1]),
                    pnl=FVal(row[2]),
                )
                for row in result
            ]
        elif validator_indices is not None:
            # Use ORM for simple IN query
            statement = sqlmodel_select(Eth2DailyStakingDetails).where(
                Eth2DailyStakingDetails.validator_index.in_(validator_indices)
            )
            result = await self.session.execute(statement)
            details = result.scalars().all()
            return [
                ValidatorDailyStats(
                    validator_index=detail.validator_index,
                    timestamp=Timestamp(detail.timestamp),
                    pnl=FVal(detail.pnl),
                )
                for detail in details
            ]
        else:
            # Use ORM for simple select all
            statement = sqlmodel_select(Eth2DailyStakingDetails)
            result = await self.session.execute(statement)
            details = result.scalars().all()
            return [
                ValidatorDailyStats(
                    validator_index=detail.validator_index,
                    timestamp=Timestamp(detail.timestamp),
                    pnl=FVal(detail.pnl),
                )
                for detail in details
            ]
    
    async def validator_exists(self, pubkey: Eth2PubKey | None, index: int | None) -> bool:
        """Checks if validator exists by pubkey or index"""
        if pubkey is not None:
            statement = sqlmodel_select(Eth2Validator).where(Eth2Validator.public_key == pubkey)
            result = await self.session.execute(statement)
            validator = result.scalar_one_or_none()
            return validator is not None
        elif index is not None:
            statement = sqlmodel_select(Eth2Validator).where(Eth2Validator.validator_index == index)
            result = await self.session.execute(statement)
            validator = result.scalar_one_or_none()
            return validator is not None
        else:
            return False
    
    async def get_active_pubkeys_to_ownership(self) -> dict[Eth2PubKey, FVal]:
        """Get mapping of active validator pubkeys to ownership proportion"""
        # Note: This query uses complex NOT IN subquery with join
        # Keeping raw SQL for performance
        result = await self.session.execute(
            text("""
                SELECT public_key, ownership_proportion FROM eth2_validators V
                WHERE V.validator_index NOT IN (
                    SELECT S.validator_index FROM eth_staking_events_info S
                    LEFT JOIN history_events H ON S.identifier=H.identifier
                    WHERE S.is_exit_or_blocknumber=1
                )
            """)
        )
        return {Eth2PubKey(row[0]): FVal(row[1]) for row in result}
    
    async def get_index_to_ownership(self) -> dict[int, FVal]:
        """Get mapping of validator indices to ownership proportion"""
        statement = sqlmodel_select(Eth2Validator.validator_index, Eth2Validator.ownership_proportion)
        result = await self.session.execute(statement)
        return {row[0]: FVal(row[1]) for row in result}
    
    async def get_validators(self) -> list[ValidatorDetails]:
        """Get all validator details"""
        statement = sqlmodel_select(Eth2Validator).order_by(Eth2Validator.validator_index)
        result = await self.session.execute(statement)
        validators = result.scalars().all()
        
        return [
            ValidatorDetails(
                validator_index=validator.validator_index,
                public_key=Eth2PubKey(validator.public_key),
                ownership_proportion=FVal(validator.ownership_proportion),
                withdrawal_address=ChecksumEvmAddress(validator.withdrawal_address) if validator.withdrawal_address else None,
                activation_timestamp=Timestamp(validator.activation_timestamp) if validator.activation_timestamp else None,
                validator_type=validator.validator_type,
            )
            for validator in validators
        ]
    
    async def get_validators_with_status(
        self,
        filter_query: Any | None = None,
    ) -> list[ValidatorDetailsWithStatus]:
        """Get validators with their status (active/exited)"""
        validators = await self.get_validators()
        
        # Get exited validators
        result = await self.session.execute(
            text("""
                SELECT DISTINCT S.validator_index FROM eth_staking_events_info S
                LEFT JOIN history_events H ON S.identifier=H.identifier
                WHERE S.is_exit_or_blocknumber=1
            """)
        )
        exited_indices = {row[0] for row in result}
        
        # Build result with status
        results = []
        for validator in validators:
            status = ValidatorDetailsWithStatus(
                validator=validator,
                is_exited=validator.validator_index in exited_indices,
            )
            
            # Apply filter if provided
            if filter_query is None or filter_query.matches(status):
                results.append(status)
        
        return results
    
    async def add_or_update_validators(
        self,
        validators: list[ValidatorDetails],
    ) -> None:
        """Add or update validators in the database"""
        for validator in validators:
            # Check if validator exists
            statement = sqlmodel_select(Eth2Validator).where(
                Eth2Validator.validator_index == validator.validator_index
            )
            result = await self.session.execute(statement)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing validator
                existing.public_key = validator.public_key
                existing.ownership_proportion = str(validator.ownership_proportion)
                existing.withdrawal_address = validator.withdrawal_address
                existing.activation_timestamp = validator.activation_timestamp
                existing.validator_type = 0  # Default type
            else:
                # Create new validator
                new_validator = Eth2Validator(
                    validator_index=validator.validator_index,
                    public_key=validator.public_key,
                    ownership_proportion=str(validator.ownership_proportion),
                    withdrawal_address=validator.withdrawal_address,
                    activation_timestamp=validator.activation_timestamp,
                    validator_type=0,  # Default type
                )
                self.session.add(new_validator)
        
        await self.session.commit()
    
    async def edit_validator_ownership(
        self,
        validator_index: int,
        ownership_proportion: FVal,
    ) -> None:
        """Edit validator ownership proportion"""
        statement = sqlmodel_select(Eth2Validator).where(
            Eth2Validator.validator_index == validator_index
        )
        result = await self.session.execute(statement)
        validator = result.scalar_one_or_none()
        
        if not validator:
            raise InputError(f'Validator {validator_index} does not exist')
        
        validator.ownership_proportion = str(ownership_proportion)
        await self.session.commit()
    
    async def delete_validators(self, validator_indices: list[int]) -> None:
        """Delete validators by their indices"""
        if not validator_indices:
            return
        
        # Delete daily stats first (using ORM)
        statement = sqlmodel_select(Eth2DailyStakingDetails).where(
            Eth2DailyStakingDetails.validator_index.in_(validator_indices)
        )
        result = await self.session.execute(statement)
        stats_to_delete = result.scalars().all()
        for stat in stats_to_delete:
            await self.session.delete(stat)
        
        # Delete validators (using ORM)
        statement = sqlmodel_select(Eth2Validator).where(
            Eth2Validator.validator_index.in_(validator_indices)
        )
        result = await self.session.execute(statement)
        validators_to_delete = result.scalars().all()
        for validator in validators_to_delete:
            await self.session.delete(validator)
        
        await self.session.commit()
    
    async def get_performance_stats(
        self,
        validator_indices: list[int] | None = None,
        from_ts: Timestamp | None = None,
        to_ts: Timestamp | None = None,
    ) -> dict[int, FVal]:
        """Get performance stats (total PnL) for validators"""
        # Note: GROUP BY aggregation query - keeping raw SQL for performance
        query = "SELECT validator_index, SUM(pnl) FROM eth2_daily_staking_details"
        conditions = []
        params = {}
        
        if validator_indices:
            placeholders = ','.join([f':idx{i}' for i in range(len(validator_indices))])
            conditions.append(f"validator_index IN ({placeholders})")
            params.update({f'idx{i}': idx for i, idx in enumerate(validator_indices)})
        
        if from_ts:
            conditions.append("timestamp >= :from_ts")
            params['from_ts'] = from_ts
        
        if to_ts:
            conditions.append("timestamp <= :to_ts")
            params['to_ts'] = to_ts
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " GROUP BY validator_index"
        
        result = await self.session.execute(text(query), params)
        return {row[0]: FVal(row[1]) for row in result}
    
    async def count_validators(self) -> int:
        """Count total number of validators"""
        from sqlalchemy import func
        statement = sqlmodel_select(func.count(Eth2Validator.identifier))
        result = await self.session.execute(statement)
        return result.scalar() or 0
    
    async def count_daily_stats(self) -> int:
        """Count total number of daily stats entries"""
        from sqlalchemy import func
        statement = sqlmodel_select(func.count()).select_from(Eth2DailyStakingDetails)
        result = await self.session.execute(statement)
        return result.scalar() or 0