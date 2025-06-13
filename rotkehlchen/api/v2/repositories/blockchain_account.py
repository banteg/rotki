"""Repository for managing blockchain accounts."""
from typing import TYPE_CHECKING, Optional

from sqlmodel import select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.user.accounts import BlockchainAccount, EvmAccountDetails
from rotkehlchen.db.models.user.models import TagMapping

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain


class BlockchainAccountRepository(BaseRepository[BlockchainAccount]):
    """Repository for managing blockchain accounts."""

    model = BlockchainAccount

    def get_accounts_by_blockchain(
        self,
        blockchain: 'SupportedBlockchain',
    ) -> list[BlockchainAccount]:
        """Get all accounts for a specific blockchain."""
        query = select(self.model).where(self.model.blockchain == blockchain.value)
        result = self.session.exec(query)
        return list(result.all())

    def get_account_details(
        self,
        address: 'ChecksumEvmAddress',
    ) -> EvmAccountDetails | None:
        """Get EVM account details for a specific address."""
        query = select(EvmAccountDetails).where(EvmAccountDetails.account == address)
        result = self.session.exec(query).first()
        return result

    def add_account(
        self,
        blockchain: 'SupportedBlockchain',
        address: str,
        label: str | None = None,
    ) -> BlockchainAccount:
        """Add a new blockchain account."""
        account_data = {
            'blockchain': blockchain.value,
            'account': address,
            'label': label,
        }
        return self.create(account_data)

    def remove_account(
        self,
        blockchain: 'SupportedBlockchain',
        address: str,
    ) -> bool:
        """Remove a blockchain account."""
        query = select(self.model).where(
            self.model.blockchain == blockchain.value,
            self.model.account == address,
        )
        account = self.session.exec(query).first()

        if account:
            self.session.delete(account)
            self.session.commit()
            return True
        return False

    def update_label(
        self,
        blockchain: 'SupportedBlockchain',
        address: str,
        label: str | None,
    ) -> BlockchainAccount | None:
        """Update the label of a blockchain account."""
        query = select(self.model).where(
            self.model.blockchain == blockchain.value,
            self.model.account == address,
        )
        account = self.session.exec(query).first()

        if account:
            account.label = label
            self.session.add(account)
            self.session.commit()
            return account
        return None

    def get_accounts_with_tags(
        self,
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> list[tuple[BlockchainAccount, list[str]]]:
        """Get accounts with their associated tags."""
        query = select(self.model)

        if blockchain:
            query = query.where(self.model.blockchain == blockchain.value)

        accounts = list(self.session.exec(query).all())

        result = []
        for account in accounts:
            # Get tags for this account
            tags_query = select(TagMapping.tag).where(
                TagMapping.object_reference == f'{account.blockchain}_{account.account}',
            )
            tags = list(self.session.exec(tags_query).all())
            result.append((account, tags))

        return result

    def get_all_evm_accounts(self) -> list[BlockchainAccount]:
        """Get all EVM accounts across all EVM chains."""
        evm_chains = [
            'eth', 'optimism', 'polygon_pos', 'arbitrum_one', 'base',
            'gnosis', 'zkevm', 'zksync_era', 'avalanche', 'scroll',
        ]

        query = select(self.model).where(self.model.blockchain.in_(evm_chains))
        result = self.session.exec(query)
        return list(result.all())

    def account_exists(
        self,
        blockchain: 'SupportedBlockchain',
        address: str,
    ) -> bool:
        """Check if an account exists."""
        query = select(self.model).where(
            self.model.blockchain == blockchain.value,
            self.model.account == address,
        )
        result = self.session.exec(query).first()
        return result is not None
