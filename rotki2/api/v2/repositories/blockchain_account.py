"""Repository for managing blockchain accounts."""
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.accounts import BlockchainAccount, EvmAccountDetails
from rotki2.db.models.user.models import TagMapping
from rotki2.db.models.user.address_book import AddressBook

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
    
    async def add_blockchain_accounts(
        self,
        accounts_data: list[dict[str, Any]],
    ) -> list[BlockchainAccount]:
        """Bulk add multiple blockchain accounts.
        
        Args:
            accounts_data: List of dicts with keys: blockchain, address, label, tags
            
        Returns:
            List of created blockchain accounts
        """
        created_accounts = []
        
        for data in accounts_data:
            # Check if account already exists
            exists = await self.account_exists(
                blockchain=data['blockchain'],
                address=data['address'],
            )
            
            if not exists:
                account = await self.add_account(
                    blockchain=data['blockchain'],
                    address=data['address'],
                    label=data.get('label'),
                )
                created_accounts.append(account)
                
                # Add tags if provided
                if 'tags' in data and data['tags']:
                    for tag in data['tags']:
                        mapping = TagMapping(
                            object_reference=f"{data['blockchain'].value}_{data['address']}",
                            tag_name=tag,
                        )
                        self.session.add(mapping)
                        
        await self.session.commit()
        return created_accounts
    
    async def edit_blockchain_accounts(
        self,
        accounts_data: list[dict[str, Any]],
    ) -> list[BlockchainAccount]:
        """Bulk edit blockchain account labels and tags.
        
        Args:
            accounts_data: List of dicts with keys: blockchain, address, label, tags
            
        Returns:
            List of updated blockchain accounts
        """
        updated_accounts = []
        
        for data in accounts_data:
            account = await self.update_label(
                blockchain=data['blockchain'],
                address=data['address'],
                label=data.get('label'),
            )
            
            if account:
                updated_accounts.append(account)
                
                # Update tags if provided
                if 'tags' in data:
                    # Remove existing tags
                    ref = f"{data['blockchain'].value}_{data['address']}"
                    await self.session.exec(
                        select(TagMapping).where(
                            col(TagMapping.object_reference) == ref
                        )
                    )
                    # TODO: Delete existing tags
                    
                    # Add new tags
                    for tag in data.get('tags', []):
                        mapping = TagMapping(
                            object_reference=ref,
                            tag_name=tag,
                        )
                        self.session.add(mapping)
                        
        await self.session.commit()
        return updated_accounts
    
    async def get_blockchain_account_data(
        self,
        blockchain: 'SupportedBlockchain' | None = None,
    ) -> list[dict[str, Any]]:
        """Get comprehensive blockchain account data with labels and tags.
        
        Returns account data including address book labels and tags.
        """
        # Build base query
        query = select(
            BlockchainAccount,
            AddressBook.name.label('address_book_label'),
        ).select_from(BlockchainAccount).outerjoin(
            AddressBook,
            (BlockchainAccount.account == AddressBook.address) &
            ((AddressBook.blockchain == BlockchainAccount.blockchain) |
             (AddressBook.blockchain.is_(None)))
        )
        
        if blockchain:
            query = query.where(col(BlockchainAccount.blockchain) == blockchain.value)
            
        result = await self.session.exec(query)
        rows = result.all()
        
        account_data = []
        for row in rows:
            account = row[0]
            address_book_label = row[1]
            
            # Get tags for this account
            tags_result = await self.session.exec(
                select(TagMapping.tag_name).where(
                    col(TagMapping.object_reference) == f'{account.blockchain}_{account.account}'
                )
            )
            tags = list(tags_result.all())
            
            account_data.append({
                'blockchain': account.blockchain,
                'address': account.account,
                'label': account.label or address_book_label,
                'tags': tags,
            })
            
        return account_data
    
    async def get_blockchains_for_accounts(
        self,
        addresses: list[str],
    ) -> dict[str, list[str]]:
        """Get which blockchains the given addresses belong to.
        
        Returns:
            Dict mapping address to list of blockchain names
        """
        result = await self.session.exec(
            select(BlockchainAccount).where(
                col(BlockchainAccount.account).in_(addresses)
            )
        )
        accounts = result.all()
        
        address_chains = {}
        for account in accounts:
            if account.account not in address_chains:
                address_chains[account.account] = []
            address_chains[account.account].append(account.blockchain)
            
        return address_chains
    
    async def get_tokens_for_address(
        self,
        address: 'ChecksumEvmAddress',
    ) -> list[str] | None:
        """Get detected tokens for an EVM address.
        
        Returns:
            List of token identifiers or None if not cached
        """
        details = await self.get_account_details(address)
        if details and details.tokens_list:
            # TODO: Filter out ignored tokens
            return details.tokens_list.split(',')
        return None
    
    async def save_tokens_for_address(
        self,
        address: 'ChecksumEvmAddress',
        tokens: list[str],
        timestamp: int,
    ) -> None:
        """Save detected tokens for an EVM address."""
        details = await self.get_account_details(address)
        
        if details:
            details.tokens_list = ','.join(tokens)
            details.last_queried_timestamp = timestamp
        else:
            details = EvmAccountDetails(
                account=address,
                tokens_list=','.join(tokens),
                last_queried_timestamp=timestamp,
            )
            self.session.add(details)
            
        await self.session.commit()
    
    async def remove_blockchain_accounts(
        self,
        accounts: list[tuple['SupportedBlockchain', str]],
    ) -> int:
        """Bulk remove blockchain accounts.
        
        Args:
            accounts: List of (blockchain, address) tuples
            
        Returns:
            Number of accounts removed
        """
        removed = 0
        
        for blockchain, address in accounts:
            if await self.remove_account(blockchain, address):
                removed += 1
                
        return removed
