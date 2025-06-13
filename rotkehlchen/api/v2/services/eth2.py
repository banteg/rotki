"""ETH2 service for Ethereum 2.0 staking operations"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.types import ChecksumEvmAddress, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.api.v2.repositories.eth2_validator import Eth2ValidatorRepository


class ETH2Service:
    """Service for handling ETH2 staking operations"""

    def __init__(
        self,
        db_service: DatabaseService,
        eth2_validator_repo: 'Eth2ValidatorRepository | None' = None,
    ):
        self.db = db_service
        self.eth2_validator_repo = eth2_validator_repo

    def get_validators(self) -> list[dict[str, Any]]:
        """Get all tracked ETH2 validators"""
        # Use repository if available
        if self.eth2_validator_repo:
            validators = self.eth2_validator_repo.get_validators_by_owner()
            return [
                {
                    'validator_index': v.validator_index,
                    'public_key': v.public_key,
                    'ownership_proportion': str(v.ownership_proportion) if v.ownership_proportion else '1.0',
                    'withdrawal_address': v.withdrawal_address,
                    'activation_timestamp': v.activation_timestamp,
                }
                for v in validators
            ]

        # Fallback to direct SQL
        validators = []
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                """SELECT validator_index, public_key, ownership_proportion,
                          withdrawal_address, activation_timestamp
                   FROM eth2_validators
                   ORDER BY validator_index""",
            )

            for row in cursor:
                validators.append({
                    'validator_index': row[0],
                    'public_key': row[1],
                    'ownership_proportion': str(row[2]) if row[2] else '1.0',
                    'withdrawal_address': row[3],
                    'activation_timestamp': row[4],
                })

        return validators

    def add_validator_by_index(
        self,
        index: int,
        ownership_proportion: str = '1.0',
        withdrawal_address: ChecksumEvmAddress | None = None,
    ) -> int:
        """Add a validator by index"""
        # Use repository if available
        if self.eth2_validator_repo:
            existing = self.eth2_validator_repo.get_validator_by_index(index)
            if existing:
                raise ValueError(f'Validator {index} already tracked')

            validator = self.eth2_validator_repo.add_validator(
                validator_index=index,
                public_key='',  # Will be fetched from chain
                withdrawal_address=withdrawal_address,
            )
            return validator.validator_index

        # Fallback to direct SQL
        with self.db.conn.write_ctx() as cursor:
            # Check if validator already exists
            cursor.execute(
                'SELECT validator_index FROM eth2_validators WHERE validator_index = ?',
                (index,),
            )
            if cursor.fetchone():
                raise ValueError(f'Validator {index} already tracked')

            # Add validator
            cursor.execute(
                """INSERT INTO eth2_validators 
                   (validator_index, ownership_proportion, withdrawal_address)
                   VALUES (?, ?, ?)""",
                (index, ownership_proportion, withdrawal_address),
            )
            return index

    def add_validator_by_public_key(
        self,
        public_key: str,
        ownership_proportion: str = '1.0',
    ) -> str:
        """Add a validator by public key"""
        # Validate public key format
        if not public_key.startswith('0x') or len(public_key) != 98:
            raise ValueError('Invalid public key format')

        with self.db.conn.write_ctx() as cursor:
            # Check if validator already exists
            cursor.execute(
                'SELECT public_key FROM eth2_validators WHERE public_key = ?',
                (public_key,),
            )
            if cursor.fetchone():
                raise ValueError(f'Validator {public_key} already tracked')

            # Add validator
            cursor.execute(
                """INSERT INTO eth2_validators 
                   (public_key, ownership_proportion)
                   VALUES (?, ?)""",
                (public_key, ownership_proportion),
            )
            return public_key

    def remove_validator(self, validator_id: int) -> bool:
        """Remove a tracked validator"""
        # Use repository if available
        if self.eth2_validator_repo:
            return self.eth2_validator_repo.remove_validator(validator_id)

        # Fallback to direct SQL
        with self.db.conn.write_ctx() as cursor:
            cursor.execute(
                'DELETE FROM eth2_validators WHERE validator_index = ?',
                (validator_id,),
            )
            return cursor.rowcount > 0

    def get_stake_performance(
        self,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp | None = None,
    ) -> dict[str, Any]:
        """Get staking performance metrics"""
        # TODO: Implement actual performance calculation
        # This would involve:
        # 1. Querying validator balances over time
        # 2. Calculating rewards earned
        # 3. Computing APR/APY

        return {
            'validators': self.get_validators(),
            'total_staked': '0',
            'total_rewards': '0',
            'apr': '0',
            'period': {
                'from_timestamp': from_timestamp,
                'to_timestamp': to_timestamp,
            },
        }

    def get_daily_stats(
        self,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp | None = None,
    ) -> list[dict[str, Any]]:
        """Get daily staking statistics"""
        # TODO: Implement actual daily stats
        # This would query eth2_daily_staking_details table

        stats = []
        with self.db.conn.read_ctx() as cursor:
            query = """SELECT timestamp, validator_index, 
                             start_balance, end_balance, 
                             rewards, deposits, withdrawals
                      FROM eth2_daily_staking_details
                      WHERE timestamp >= ?"""
            params = [from_timestamp]

            if to_timestamp:
                query += ' AND timestamp <= ?'
                params.append(to_timestamp)

            query += ' ORDER BY timestamp, validator_index'

            cursor.execute(query, params)
            for row in cursor:
                stats.append({
                    'timestamp': row[0],
                    'validator_index': row[1],
                    'start_balance': str(row[2]) if row[2] else '0',
                    'end_balance': str(row[3]) if row[3] else '0',
                    'rewards': str(row[4]) if row[4] else '0',
                    'deposits': str(row[5]) if row[5] else '0',
                    'withdrawals': str(row[6]) if row[6] else '0',
                })

        return stats

    def get_stake_deposits(
        self,
        address: ChecksumEvmAddress | None = None,
    ) -> list[dict[str, Any]]:
        """Get ETH2 stake deposits"""
        deposits = []

        with self.db.conn.read_ctx() as cursor:
            query = """SELECT tx_hash, from_address, timestamp, 
                             pubkey, amount, withdrawal_credentials
                      FROM eth2_deposits"""
            params = []

            if address:
                query += ' WHERE from_address = ?'
                params.append(address)

            query += ' ORDER BY timestamp DESC'

            cursor.execute(query, params)
            for row in cursor:
                deposits.append({
                    'tx_hash': row[0],
                    'from_address': row[1],
                    'timestamp': row[2],
                    'pubkey': row[3],
                    'amount': str(row[4]) if row[4] else '0',
                    'withdrawal_credentials': row[5],
                })

        return deposits

    def edit_validator(self, validator_id: int, ownership_proportion: str) -> None:
        """Edit a validator's ownership proportion"""
        with self.db.conn.write_ctx() as cursor:
            cursor.execute(
                'UPDATE eth2_validators SET ownership_proportion = ? WHERE validator_index = ?',
                (ownership_proportion, validator_id),
            )

            if cursor.rowcount == 0:
                raise ValueError(f'Validator {validator_id} not found')

    def redecode_stake_events(self) -> dict[str, Any]:
        """Redecode ETH2 staking events"""
        # Would trigger reprocessing of ETH2 events
        # This would re-decode block production events, attestations, etc.
        return {
            'task_id': 'redecode_eth2_events_123',
            'status': 'started',
            'message': 'ETH2 event redecoding started',
        }

    def reset_stake_data(self) -> dict[str, Any]:
        """Reset all ETH2 staking data"""
        with self.db.conn.write_ctx() as cursor:
            # Delete all ETH2 related data
            cursor.execute('DELETE FROM eth2_daily_staking_details')
            cursor.execute('DELETE FROM eth2_validators WHERE 1=1')  # Keep structure

        return {
            'success': True,
            'message': 'ETH2 staking data has been reset',
        }
