"""Blockchain accounts management using ORM"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.db.orm.database import RotkehlchenDatabase
from rotkehlchen.errors.misc import InputError, TagConstraintError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    BTCAddress,
    ChecksumEvmAddress,
    ListOfBlockchainAddresses,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BlockchainAccountsManager:
    """Manages blockchain accounts using ORM"""
    
    def __init__(self, database: RotkehlchenDatabase, chains_aggregator: 'ChainsAggregator'):
        self.db = database
        self.chains_aggregator = chains_aggregator
    
    def get_blockchain_accounts(self) -> ListOfBlockchainAddresses:
        """Get all blockchain accounts from database using ORM"""
        accounts = ListOfBlockchainAddresses()
        
        # Get all accounts from repository
        all_accounts = self.db.repos.accounts.get_all_accounts()
        
        # Group by blockchain
        for account in all_accounts:
            blockchain = SupportedBlockchain.deserialize(account.blockchain)
            address = account.account
            
            # Add to appropriate list based on blockchain
            if blockchain == SupportedBlockchain.BITCOIN:
                accounts.btc.append(BTCAddress(address))
            elif blockchain == SupportedBlockchain.BITCOIN_CASH:
                accounts.bch.append(BTCAddress(address))
            elif blockchain == SupportedBlockchain.ETHEREUM:
                accounts.eth.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.OPTIMISM:
                accounts.optimism.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.POLYGON_POS:
                accounts.polygon_pos.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.ARBITRUM_ONE:
                accounts.arbitrum_one.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.BASE:
                accounts.base.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.GNOSIS:
                accounts.gnosis.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.SCROLL:
                accounts.scroll.append(ChecksumEvmAddress(address))
            elif blockchain == SupportedBlockchain.ZKSYNC_LITE:
                accounts.zksync_lite.append(ChecksumEvmAddress(address))
            # TODO: Add other blockchains as needed
        
        return accounts
    
    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: list[str],
            labels: list[str | None] | None = None,
            tags: list[list[str] | None] | None = None,
    ) -> list[str]:
        """Add blockchain accounts using ORM
        
        Returns list of addresses that were actually added (not duplicates)
        """
        if labels is not None and len(labels) != len(accounts):
            raise InputError(
                f'Number of labels ({len(labels)}) does not match '
                f'number of accounts ({len(accounts)})'
            )
        
        if tags is not None and len(tags) != len(accounts):
            raise InputError(
                f'Number of tag lists ({len(tags)}) does not match '
                f'number of accounts ({len(accounts)})'
            )
        
        added_accounts = []
        
        with self.db.repos.unit_of_work():
            for idx, address in enumerate(accounts):
                # Check if account already exists
                existing = self.db.repos.accounts.get_account(
                    blockchain=blockchain.serialize(),
                    address=address,
                )
                
                if existing:
                    log.warning(f'Account {address} already exists on {blockchain}')
                    continue
                
                # Add the account
                label = labels[idx] if labels else None
                account_tags = tags[idx] if tags else []
                
                self.db.repos.accounts.add_account(
                    blockchain=blockchain.serialize(),
                    address=address,
                    label=label,
                )
                
                # Add tags if specified
                if account_tags:
                    for tag in account_tags:
                        # Verify tag exists
                        if not self.db.repos.tags.get_tag(tag):
                            raise TagConstraintError(
                                f'Tag "{tag}" does not exist. '
                                f'Please create it first.'
                            )
                        
                        self.db.repos.tags.add_tag_mapping(
                            tag_name=tag,
                            account=address,
                            blockchain=blockchain.serialize(),
                        )
                
                added_accounts.append(address)
                
                # Notify chains aggregator
                self.chains_aggregator.accounts_added(
                    blockchain=blockchain,
                    accounts=[address],
                )
        
        return added_accounts
    
    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: list[str],
    ) -> list[str]:
        """Remove blockchain accounts using ORM
        
        Returns list of addresses that were actually removed
        """
        removed_accounts = []
        
        with self.db.repos.unit_of_work():
            for address in accounts:
                # Check if account exists
                existing = self.db.repos.accounts.get_account(
                    blockchain=blockchain.serialize(),
                    address=address,
                )
                
                if not existing:
                    log.warning(f'Account {address} does not exist on {blockchain}')
                    continue
                
                # Remove the account (this cascades to tag mappings)
                success = self.db.repos.accounts.delete_account(
                    blockchain=blockchain.serialize(),
                    address=address,
                )
                
                if success:
                    removed_accounts.append(address)
                    
                    # Notify chains aggregator
                    self.chains_aggregator.accounts_removed(
                        blockchain=blockchain,
                        accounts=[address],
                    )
        
        return removed_accounts
    
    def edit_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            address: str,
            label: str | None,
            tags: list[str] | None,
    ) -> None:
        """Edit blockchain account label and tags using ORM"""
        with self.db.repos.unit_of_work():
            # Update account label
            account = self.db.repos.accounts.get_account(
                blockchain=blockchain.serialize(),
                address=address,
            )
            
            if not account:
                raise InputError(f'Account {address} not found on {blockchain}')
            
            # Update label if provided
            if label is not None:
                self.db.repos.accounts.update_account_label(
                    blockchain=blockchain.serialize(),
                    address=address,
                    label=label,
                )
            
            # Update tags if provided
            if tags is not None:
                # First verify all tags exist
                for tag in tags:
                    if not self.db.repos.tags.get_tag(tag):
                        raise TagConstraintError(
                            f'Tag "{tag}" does not exist. '
                            f'Please create it first.'
                        )
                
                # Remove existing mappings
                self.db.repos.tags.remove_tag_mappings(
                    account=address,
                    blockchain=blockchain.serialize(),
                )
                
                # Add new mappings
                for tag in tags:
                    self.db.repos.tags.add_tag_mapping(
                        tag_name=tag,
                        account=address,
                        blockchain=blockchain.serialize(),
                    )
    
    def get_blockchain_account_data(
            self,
            blockchain: SupportedBlockchain,
    ) -> list[dict[str, Any]]:
        """Get detailed blockchain account data using ORM"""
        accounts_data = []
        
        # Get accounts for this blockchain
        accounts = self.db.repos.accounts.get_accounts_by_blockchain(
            blockchain=blockchain.serialize()
        )
        
        for account in accounts:
            # Get tags for this account
            tags = self.db.repos.accounts.get_account_tags(
                address=account.account,
                blockchain=blockchain.serialize(),
            )
            
            # Get last known balance (if available)
            # TODO: This would need to be implemented based on balance tracking
            
            accounts_data.append({
                'address': account.account,
                'label': account.label,
                'tags': tags,
            })
        
        return accounts_data
    
    def get_accounts_by_tag(self, tag_name: str) -> dict[str, list[str]]:
        """Get all accounts that have a specific tag"""
        result = defaultdict(list)
        
        # Get all accounts with this tag
        accounts = self.db.repos.tags.get_accounts_for_tag(tag_name)
        
        for address, blockchain in accounts:
            result[blockchain].append(address)
        
        return dict(result)
    
    # XPub Management
    
    def add_xpub(self, xpub_data: XpubData) -> None:
        """Add an extended public key using ORM"""
        with self.db.repos.unit_of_work():
            # Check if xpub already exists
            existing = self.db.repos.xpubs.get_xpub(xpub_data.xpub.xpub)
            if existing:
                raise InputError(f'Xpub {xpub_data.xpub.xpub} already exists')
            
            # Add xpub
            self.db.repos.xpubs.add_xpub(
                xpub=xpub_data.xpub.xpub,
                derivation_path=xpub_data.derivation_path,
                label=xpub_data.label,
                blockchain=xpub_data.blockchain.serialize(),
            )
            
            # Add tags if any
            if xpub_data.tags:
                for tag in xpub_data.tags:
                    # Verify tag exists
                    if not self.db.repos.tags.get_tag(tag):
                        raise TagConstraintError(
                            f'Tag "{tag}" does not exist. '
                            f'Please create it first.'
                        )
                    
                    # TODO: Implement xpub tag mapping
                    # This might need a new table/model
    
    def remove_xpub(self, xpub: str) -> None:
        """Remove an extended public key using ORM"""
        with self.db.repos.unit_of_work():
            success = self.db.repos.xpubs.delete_xpub(xpub)
            if not success:
                raise InputError(f'Xpub {xpub} not found')
    
    def get_xpubs(self) -> list[XpubData]:
        """Get all extended public keys using ORM"""
        xpubs_data = []
        
        all_xpubs = self.db.repos.xpubs.get_all_xpubs()
        
        for xpub_entry in all_xpubs:
            # TODO: Convert ORM model to XpubData
            # This requires proper initialization of XpubData
            pass
        
        return xpubs_data