"""Async Eth2 service for ETH2/staking operations"""
from typing import TYPE_CHECKING, Any

from rotki2.api.v2.repositories.async_eth2 import AsyncEth2Repository
from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    ValidatorDailyStats,
    ValidatorDetails,
    ValidatorDetailsWithStatus,
)
from rotkehlchen.constants import ONE
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp

if TYPE_CHECKING:
    from collections.abc import Collection


class AsyncEth2Service:
    """Async service for ETH2/staking operations"""
    
    def __init__(
        self,
        eth2_repository: AsyncEth2Repository,
    ):
        self.eth2_repository = eth2_repository
    
    async def add_validator(
        self,
        validator_index: int,
        public_key: Eth2PubKey,
        ownership_proportion: FVal = ONE,
        withdrawal_address: ChecksumEvmAddress | None = None,
        activation_timestamp: Timestamp | None = None,
    ) -> dict[str, Any]:
        """Add a new validator.
        
        Returns:
            Dict with success message
        """
        # Check if validator already exists
        if await self.eth2_repository.validator_exists(pubkey=public_key, index=None):
            raise InputError(f'Validator with public key {public_key} already exists')
        
        if await self.eth2_repository.validator_exists(pubkey=None, index=validator_index):
            raise InputError(f'Validator with index {validator_index} already exists')
        
        validator = ValidatorDetails(
            validator_index=validator_index,
            public_key=public_key,
            ownership_proportion=ownership_proportion,
            withdrawal_address=withdrawal_address,
            activation_timestamp=activation_timestamp,
            validator_type=0,
        )
        
        await self.eth2_repository.add_or_update_validators([validator])
        
        return {'message': f'Successfully added validator {validator_index}'}
    
    async def edit_validator_ownership(
        self,
        validator_index: int,
        ownership_proportion: FVal,
    ) -> dict[str, Any]:
        """Edit validator ownership proportion.
        
        Returns:
            Dict with success message
        """
        if ownership_proportion <= 0 or ownership_proportion > ONE:
            raise InputError('Ownership proportion must be between 0 and 1')
        
        await self.eth2_repository.edit_validator_ownership(
            validator_index=validator_index,
            ownership_proportion=ownership_proportion,
        )
        
        return {'message': f'Successfully updated ownership for validator {validator_index}'}
    
    async def delete_validators(
        self,
        validator_indices: list[int],
    ) -> dict[str, Any]:
        """Delete validators by their indices.
        
        Returns:
            Dict with number of validators deleted
        """
        if not validator_indices:
            raise InputError('No validator indices provided')
        
        await self.eth2_repository.delete_validators(validator_indices)
        
        return {'deleted': len(validator_indices)}
    
    async def get_validators(
        self,
        filter_query: Any | None = None,
    ) -> dict[str, Any]:
        """Get validators with optional filtering.
        
        Returns:
            Dict with validator list and metadata
        """
        if filter_query:
            validators_with_status = await self.eth2_repository.get_validators_with_status(
                filter_query=filter_query,
            )
            
            # Serialize validators
            serialized = []
            for vws in validators_with_status:
                data = {
                    'validator_index': vws.validator.validator_index,
                    'public_key': vws.validator.public_key,
                    'ownership_proportion': str(vws.validator.ownership_proportion),
                    'withdrawal_address': vws.validator.withdrawal_address,
                    'activation_timestamp': vws.validator.activation_timestamp,
                    'is_exited': vws.is_exited,
                }
                serialized.append(data)
        else:
            validators = await self.eth2_repository.get_validators()
            serialized = []
            for v in validators:
                data = {
                    'validator_index': v.validator_index,
                    'public_key': v.public_key,
                    'ownership_proportion': str(v.ownership_proportion),
                    'withdrawal_address': v.withdrawal_address,
                    'activation_timestamp': v.activation_timestamp,
                }
                serialized.append(data)
        
        total_count = await self.eth2_repository.count_validators()
        
        return {
            'entries': serialized,
            'entries_found': len(serialized),
            'entries_total': total_count,
        }
    
    async def get_validator_daily_stats(
        self,
        filter_query: Eth2DailyStatsFilterQuery | None = None,
        validator_indices: list[int] | None = None,
    ) -> dict[str, Any]:
        """Get validator daily stats with optional filtering.
        
        Returns:
            Dict with stats list and metadata
        """
        if filter_query:
            stats, total_count, eth_sum = await self.eth2_repository.get_validator_daily_stats_and_limit_info(
                filter_query=filter_query,
            )
        else:
            stats = await self.eth2_repository.get_validator_daily_stats(
                validator_indices=validator_indices,
            )
            total_count = len(stats)
            eth_sum = sum(s.pnl for s in stats)
        
        # Serialize stats
        serialized = []
        for stat in stats:
            data = {
                'validator_index': stat.validator_index,
                'timestamp': stat.timestamp,
                'pnl': str(stat.pnl),
            }
            serialized.append(data)
        
        return {
            'entries': serialized,
            'entries_found': len(serialized),
            'entries_total': total_count,
            'sum_pnl': str(eth_sum),
        }
    
    async def add_validator_daily_stats(
        self,
        stats: list[ValidatorDailyStats],
    ) -> dict[str, Any]:
        """Add validator daily stats.
        
        Returns:
            Dict with number of stats added
        """
        if not stats:
            raise InputError('No stats provided')
        
        await self.eth2_repository.add_validator_daily_stats(stats)
        
        return {'added': len(stats)}
    
    async def get_validators_to_query_for_stats(
        self,
        up_to_ts: Timestamp,
    ) -> dict[str, Any]:
        """Get validators that need stats updates.
        
        Returns:
            Dict with validator list needing updates
        """
        validators = await self.eth2_repository.get_validators_to_query_for_stats(up_to_ts)
        
        # Serialize the data
        serialized = []
        for validator_index, last_queried_ts, exit_ts in validators:
            data = {
                'validator_index': validator_index,
                'last_queried_timestamp': last_queried_ts,
                'exit_timestamp': exit_ts,
            }
            serialized.append(data)
        
        return {
            'validators': serialized,
            'count': len(serialized),
        }
    
    async def get_validator_performance(
        self,
        validator_indices: list[int] | None = None,
        from_ts: Timestamp | None = None,
        to_ts: Timestamp | None = None,
    ) -> dict[str, Any]:
        """Get performance stats for validators.
        
        Returns:
            Dict with performance data per validator
        """
        performance = await self.eth2_repository.get_performance_stats(
            validator_indices=validator_indices,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        
        # Serialize performance data
        serialized = {
            str(idx): str(pnl) for idx, pnl in performance.items()
        }
        
        return {
            'performance': serialized,
            'validators_count': len(performance),
        }
    
    async def get_active_validator_stats(self) -> dict[str, Any]:
        """Get statistics about active validators.
        
        Returns:
            Dict with active validator statistics
        """
        # Get active validators with ownership
        active_pubkeys = await self.eth2_repository.get_active_pubkeys_to_ownership()
        total_validators = await self.eth2_repository.count_validators()
        
        # Calculate total ownership
        total_ownership = sum(active_pubkeys.values())
        
        return {
            'active_validators': len(active_pubkeys),
            'total_validators': total_validators,
            'total_ownership': str(total_ownership),
            'average_ownership': str(total_ownership / len(active_pubkeys)) if active_pubkeys else '0',
        }
    
    async def import_validators(
        self,
        validators_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Import validators from data.
        
        Returns:
            Dict with import statistics
        """
        imported = 0
        errors = []
        
        validators_to_add = []
        for data in validators_data:
            try:
                validator = ValidatorDetails(
                    validator_index=data['validator_index'],
                    public_key=Eth2PubKey(data['public_key']),
                    ownership_proportion=FVal(data.get('ownership_proportion', '1')),
                    withdrawal_address=ChecksumEvmAddress(data['withdrawal_address']) if data.get('withdrawal_address') else None,
                    activation_timestamp=Timestamp(data['activation_timestamp']) if data.get('activation_timestamp') else None,
                    validator_type=data.get('validator_type', 0),
                )
                validators_to_add.append(validator)
                imported += 1
            except Exception as e:
                errors.append({
                    'validator': str(data),
                    'error': str(e),
                })
        
        if validators_to_add:
            await self.eth2_repository.add_or_update_validators(validators_to_add)
        
        return {
            'imported': imported,
            'errors': errors,
        }
    
    async def export_validators(self) -> dict[str, Any]:
        """Export all validators.
        
        Returns:
            Dict with exported validator data
        """
        validators = await self.eth2_repository.get_validators()
        
        # Serialize for export
        exported = []
        for v in validators:
            data = {
                'validator_index': v.validator_index,
                'public_key': v.public_key,
                'ownership_proportion': str(v.ownership_proportion),
            }
            if v.withdrawal_address:
                data['withdrawal_address'] = v.withdrawal_address
            if v.activation_timestamp:
                data['activation_timestamp'] = v.activation_timestamp
            
            exported.append(data)
        
        return {
            'validators': exported,
            'count': len(exported),
        }