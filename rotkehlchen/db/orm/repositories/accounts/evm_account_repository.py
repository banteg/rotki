"""Repository for EVM account details management"""


from sqlalchemy import select

from rotkehlchen.db.orm.user_db_models import EvmAccountDetails
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import ChecksumEvmAddress, Timestamp


class EvmAccountDetailsRepository(BaseRepository[EvmAccountDetails]):
    """Repository for managing EVM account details"""

    def __init__(self, session):
        super().__init__(session, EvmAccountDetails)

    def add_detail(
        self,
        account: ChecksumEvmAddress,
        chain_id: int,
        key: str,
        value: str,
    ) -> EvmAccountDetails:
        """Add an account detail"""
        detail = EvmAccountDetails(
            account=account,
            chain_id=chain_id,
            key=key,
            value=value,
        )
        return self.add(detail)

    def get_details(
        self,
        account: ChecksumEvmAddress,
        chain_id: int,
        key: str | None = None,
    ) -> list[EvmAccountDetails]:
        """Get account details"""
        filters = {
            'account': account,
            'chain_id': chain_id,
        }
        if key is not None:
            filters['key'] = key

        return self.get_all(**filters)

    def get_detail_value(
        self,
        account: ChecksumEvmAddress,
        chain_id: int,
        key: str,
        value: str,
    ) -> EvmAccountDetails | None:
        """Get specific detail by key and value"""
        return self.get(
            account=account,
            chain_id=chain_id,
            key=key,
            value=value,
        )

    def set_last_queried_timestamp(
        self,
        account: ChecksumEvmAddress,
        chain_id: int,
        timestamp: Timestamp,
    ) -> None:
        """Set the last queried timestamp for an account"""
        # Remove existing timestamp
        self.delete_by(
            account=account,
            chain_id=chain_id,
            key='last_queried_timestamp',
        )

        # Add new timestamp
        self.add_detail(
            account=account,
            chain_id=chain_id,
            key='last_queried_timestamp',
            value=str(timestamp),
        )

    def get_last_queried_timestamp(
        self,
        account: ChecksumEvmAddress,
        chain_id: int,
    ) -> Timestamp | None:
        """Get the last queried timestamp for an account"""
        details = self.get_details(account, chain_id, 'last_queried_timestamp')
        if details and details[0].value:
            return Timestamp(int(details[0].value))
        return None

    def add_queried_token(
        self,
        account: ChecksumEvmAddress,
        chain_id: int,
        token_address: ChecksumEvmAddress,
    ) -> None:
        """Add a token that was queried for an account"""
        # Check if already exists
        if not self.get_detail_value(account, chain_id, 'token', token_address):
            self.add_detail(
                account=account,
                chain_id=chain_id,
                key='token',
                value=token_address,
            )

    def get_queried_tokens(
        self,
        account: ChecksumEvmAddress,
        chain_id: int,
    ) -> list[ChecksumEvmAddress]:
        """Get all tokens queried for an account"""
        details = self.get_details(account, chain_id, 'token')
        return [ChecksumEvmAddress(d.value) for d in details if d.value]

    def remove_queried_tokens(
        self,
        account: ChecksumEvmAddress,
        chain_id: int,
    ) -> int:
        """Remove all queried tokens for an account"""
        return self.delete_by(
            account=account,
            chain_id=chain_id,
            key='token',
        )

    def delete_account_details(
        self,
        account: ChecksumEvmAddress,
        chain_id: int | None = None,
    ) -> int:
        """Delete all details for an account"""
        filters = {'account': account}
        if chain_id is not None:
            filters['chain_id'] = chain_id

        return self.delete_by(**filters)

    def get_accounts_with_details(
        self,
        chain_id: int | None = None,
    ) -> list[ChecksumEvmAddress]:
        """Get all accounts that have details stored"""
        stmt = select(EvmAccountDetails.account).distinct()
        if chain_id is not None:
            stmt = stmt.filter_by(chain_id=chain_id)

        result = self.session.execute(stmt).scalars().all()
        return [ChecksumEvmAddress(acc) for acc in result]
