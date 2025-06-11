"""Service layer for account management operations"""


from rotkehlchen.chain.accounts import BlockchainAccountData, SingleBlockchainAccountData
from rotkehlchen.db.orm.repositories.accounts import (
    BlockchainAccountRepository,
    TagRepository,
)
from rotkehlchen.db.orm.repositories.unit_of_work import UnitOfWork
from rotkehlchen.types import BlockchainAccountAddress, SupportedBlockchain


class AccountService:
    """Service for managing blockchain accounts and related data"""

    def __init__(self, unit_of_work: UnitOfWork):
        self.uow = unit_of_work
        self.account_repo = BlockchainAccountRepository(self.uow.session)
        self.tag_repo = TagRepository(self.uow.session)

    def add_blockchain_account_with_tags(
        self,
        blockchain: SupportedBlockchain,
        address: BlockchainAccountAddress,
        tags: list[str] | None = None,
    ) -> None:
        """Add a blockchain account with optional tags"""
        # Add the account
        self.account_repo.add_account(blockchain, address)

        # Add tags if provided
        if tags:
            account_ref = f'{blockchain.value}_{address}'
            for tag_name in tags:
                # Ensure tag exists
                self.tag_repo.ensure_tag_exists(tag_name)
                self.tag_repo.add_tag_mapping(account_ref, tag_name)

    def remove_blockchain_accounts(
        self,
        accounts: list[SingleBlockchainAccountData],
    ) -> int:
        """Remove blockchain accounts and their associated data"""
        count = 0

        for account in accounts:
            # Remove tag mappings
            account_ref = f'{account.blockchain.value}_{account.address}'
            self.tag_repo.remove_tag_mappings(account_ref)

            # Remove the account
            if self.account_repo.remove_account(account.blockchain, account.address):
                count += 1

        return count

    def get_blockchain_accounts_data(
        self,
        blockchain: SupportedBlockchain | None = None,
    ) -> BlockchainAccountData:
        """Get all blockchain accounts organized by blockchain"""
        if blockchain:
            accounts = self.account_repo.get_accounts_by_blockchain(blockchain)
        else:
            accounts = self.account_repo.get_all_accounts()

        return self.account_repo.to_blockchain_account_data(accounts)

    def update_account_tags(
        self,
        blockchain: SupportedBlockchain,
        address: BlockchainAccountAddress,
        tags: list[str],
    ) -> None:
        """Update tags for a blockchain account"""
        # Verify account exists
        if not self.account_repo.account_exists(blockchain, address):
            raise ValueError(f'Account {address} on {blockchain} does not exist')

        account_ref = f'{blockchain.value}_{address}'

        # Remove existing tags
        self.tag_repo.remove_tag_mappings(account_ref)

        # Add new tags
        for tag_name in tags:
            self.tag_repo.ensure_tag_exists(tag_name)
            self.tag_repo.add_tag_mapping(account_ref, tag_name)

    def get_accounts_by_tag(self, tag_name: str) -> list[SingleBlockchainAccountData]:
        """Get all accounts that have a specific tag"""
        mappings = self.tag_repo.get_mappings_by_tag(tag_name)

        accounts = []
        for mapping in mappings:
            # Parse account reference (format: blockchain_address)
            parts = mapping.split('_', 1)
            if len(parts) == 2:
                blockchain = SupportedBlockchain(parts[0])
                address = BlockchainAccountAddress(parts[1])

                # Verify account still exists
                if self.account_repo.account_exists(blockchain, address):
                    accounts.append(SingleBlockchainAccountData(
                        blockchain=blockchain,
                        address=address,
                    ))

        return accounts
