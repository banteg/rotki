"""Repository for managing blockchain accounts."""
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.accounts import BlockchainAccount, EvmAccountDetails
from rotki2.db.models.user.models import TagMapping

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain


class BlockchainAccountRepository(AsyncBaseRepository[BlockchainAccount]):
    """Repository for managing blockchain accounts."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, BlockchainAccount)

    async def get_accounts_by_blockchain(
        self,
        blockchain: 'SupportedBlockchain',
    ) -> list[BlockchainAccount]:
        """Get all accounts for a specific blockchain."""
        result = await self.session.exec(
            select(BlockchainAccount).where(
                col(BlockchainAccount.blockchain) == blockchain.value
            )
        )
        return list(result.all())

    async def get_account_details(
        self,
        address: 'ChecksumEvmAddress',
    ) -> EvmAccountDetails | None:
        """Get EVM account details for a specific address."""
        result = await self.session.exec(
            select(EvmAccountDetails).where(
                col(EvmAccountDetails.account) == address
            )
        )
        return result.first()

    async def add_account(
        self,
        blockchain: 'SupportedBlockchain',
        address: str,
        label: str | None = None,
    ) -> BlockchainAccount:
        """Add a new blockchain account."""
        account = BlockchainAccount(
            blockchain=blockchain.value,
            account=address,
            label=label,
        )
        return await self.create(account)

    async def remove_account(
        self,
        blockchain: 'SupportedBlockchain',
        address: str,
    ) -> bool:
        """Remove a blockchain account."""
        result = await self.session.exec(
            select(BlockchainAccount).where(
                col(BlockchainAccount.blockchain) == blockchain.value,
                col(BlockchainAccount.account) == address,
            )
        )
        account = result.first()

        if account:
            await self.session.delete(account)
            await self.session.commit()
            return True
        return False

    async def update_label(
        self,
        blockchain: 'SupportedBlockchain',
        address: str,
        label: str | None,
    ) -> BlockchainAccount | None:
        """Update the label of a blockchain account."""
        result = await self.session.exec(
            select(BlockchainAccount).where(
                col(BlockchainAccount.blockchain) == blockchain.value,
                col(BlockchainAccount.account) == address,
            )
        )
        account = result.first()

        if account:
            account.label = label
            self.session.add(account)
            await self.session.commit()
            return account
        return None

    async def get_accounts_with_tags(
        self,
        blockchain: Optional['SupportedBlockchain'] = None,
    ) -> list[tuple[BlockchainAccount, list[str]]]:
        """Get accounts with their associated tags."""
        query = select(BlockchainAccount)

        if blockchain:
            query = query.where(col(BlockchainAccount.blockchain) == blockchain.value)

        accounts_result = await self.session.exec(query)
        accounts = list(accounts_result.all())

        result = []
        for account in accounts:
            # Get tags for this account
            tags_result = await self.session.exec(
                select(TagMapping.tag_name).where(
                    col(TagMapping.object_reference) == f'{account.blockchain}_{account.account}'
                )
            )
            tags = list(tags_result.all())
            result.append((account, tags))

        return result

    async def get_all_evm_accounts(self) -> list[BlockchainAccount]:
        """Get all EVM accounts across all EVM chains."""
        evm_chains = [
            'eth', 'optimism', 'polygon_pos', 'arbitrum_one', 'base',
            'gnosis', 'zkevm', 'zksync_era', 'avalanche', 'scroll',
        ]

        result = await self.session.exec(
            select(BlockchainAccount).where(
                col(BlockchainAccount.blockchain).in_(evm_chains)
            )
        )
        return list(result.all())

    async def account_exists(
        self,
        blockchain: 'SupportedBlockchain',
        address: str,
    ) -> bool:
        """Check if an account exists."""
        result = await self.session.exec(
            select(BlockchainAccount).where(
                col(BlockchainAccount.blockchain) == blockchain.value,
                col(BlockchainAccount.account) == address,
            )
        )
        return result.first() is not None
