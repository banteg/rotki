"""Repository for blockchain account management"""


from sqlalchemy import delete, select

from rotkehlchen.chain.accounts import BlockchainAccountData, SingleBlockchainAccountData
from rotkehlchen.db.orm.models import BlockchainAccount, tag_mappings
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import BlockchainAddress, SupportedBlockchain


class BlockchainAccountRepository(BaseRepository[BlockchainAccount]):
    """Repository for managing blockchain accounts"""

    def __init__(self, session):
        super().__init__(session, BlockchainAccount)

    def get_account(
        self,
        blockchain: SupportedBlockchain,
        address: BlockchainAddress,
    ) -> BlockchainAccount | None:
        """Get a specific blockchain account"""
        return self.get(blockchain=blockchain.value, account=address)

    def get_accounts_by_blockchain(
        self,
        blockchain: SupportedBlockchain,
    ) -> list[BlockchainAccount]:
        """Get all accounts for a specific blockchain"""
        return self.get_all(blockchain=blockchain.value)

    def get_all_accounts(self) -> list[BlockchainAccount]:
        """Get all blockchain accounts"""
        stmt = select(BlockchainAccount).order_by(
            BlockchainAccount.blockchain,
            BlockchainAccount.account,
        )
        return list(self.session.execute(stmt).scalars().all())

    def add_account(
        self,
        blockchain: SupportedBlockchain,
        address: BlockchainAddress,
    ) -> BlockchainAccount:
        """Add a new blockchain account"""
        account = BlockchainAccount(
            blockchain=blockchain.value,
            account=address,
        )
        return self.add(account)

    def add_multiple_accounts(
        self,
        accounts: list[SingleBlockchainAccountData],
    ) -> list[BlockchainAccount]:
        """Add multiple blockchain accounts"""
        db_accounts = [
            BlockchainAccount(
                blockchain=acc.blockchain.value,
                account=acc.address,
            )
            for acc in accounts
        ]
        return self.add_all(db_accounts)

    def remove_account(
        self,
        blockchain: SupportedBlockchain,
        address: BlockchainAddress,
    ) -> bool:
        """Remove a blockchain account"""
        return self.delete_by(
            blockchain=blockchain.value,
            account=address,
        ) > 0

    def remove_accounts(
        self,
        accounts: list[SingleBlockchainAccountData],
    ) -> int:
        """Remove multiple blockchain accounts"""
        count = 0
        for acc in accounts:
            count += self.delete_by(
                blockchain=acc.blockchain.value,
                account=acc.address,
            )
        return count

    def get_accounts_with_tags(
        self,
        blockchain: SupportedBlockchain | None = None,
    ) -> list[tuple[BlockchainAccount, list[str]]]:
        """Get accounts with their associated tags"""
        query = select(BlockchainAccount)

        if blockchain:
            query = query.filter_by(blockchain=blockchain.value)

        accounts = self.session.execute(query).scalars().all()

        # Get tags for each account
        result = []
        for account in accounts:
            # Query tags through tag_mappings
            tag_query = (
                select(tag_mappings.c.tag_name)
                .where(tag_mappings.c.object_reference == f'{account.blockchain}_{account.account}')
            )
            tags = [row[0] for row in self.session.execute(tag_query)]
            result.append((account, tags))

        return result

    def account_exists(
        self,
        blockchain: SupportedBlockchain,
        address: BlockchainAddress,
    ) -> bool:
        """Check if an account exists"""
        return self.exists(
            blockchain=blockchain.value,
            account=address,
        )

    def get_accounts_count(
        self,
        blockchain: SupportedBlockchain | None = None,
    ) -> int:
        """Get count of blockchain accounts"""
        if blockchain:
            return self.count(blockchain=blockchain.value)
        return self.count()

    def replace_blockchain_accounts(
        self,
        blockchain: SupportedBlockchain,
        accounts: list[BlockchainAddress],
    ) -> list[BlockchainAccount]:
        """Replace all accounts for a blockchain"""
        # Delete existing accounts
        stmt = delete(BlockchainAccount).where(
            BlockchainAccount.blockchain == blockchain.value,
        )
        self.session.execute(stmt)

        # Add new accounts
        if accounts:
            db_accounts = [
                BlockchainAccount(
                    blockchain=blockchain.value,
                    account=address,
                )
                for address in accounts
            ]
            return self.add_all(db_accounts)

        return []

    def to_blockchain_account_data(
        self,
        accounts: list[BlockchainAccount],
    ) -> BlockchainAccountData:
        """Convert database models to domain model"""
        from collections import defaultdict

        data = defaultdict(list)
        for account in accounts:
            blockchain = SupportedBlockchain(account.blockchain)
            data[blockchain].append(account.account)

        return BlockchainAccountData(dict(data))
