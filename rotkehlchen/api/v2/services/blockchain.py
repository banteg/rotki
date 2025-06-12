"""Blockchain service for blockchain-related operations"""
from typing import Any

from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain


class BlockchainService:
    """Service for blockchain operations"""

    def __init__(self, db_service: DatabaseService):
        self.db = db_service

    def get_blockchain_accounts(self, blockchain: str) -> list[BlockchainAccountData]:
        """Get accounts for a specific blockchain"""
        accounts = self.db.get_blockchain_accounts(blockchain=blockchain.value)

        # Convert to account details
        result = []
        for account in accounts:
            result.append(BlockchainAccountData(
                chain=SupportedBlockchain(blockchain),
                address=account.account,
                label=account.label if hasattr(account, 'label') else None,
                tags=account.tags if hasattr(account, 'tags') else [],
            ))

        return result

    def add_blockchain_accounts(
        self,
        blockchain: str,
        accounts: list[str],
        labels: list[str] | None = None,
        tags: list[list[str]] | None = None,
    ) -> list[str]:
        """Add multiple blockchain accounts"""
        added = []

        for i, account in enumerate(accounts):
            label = labels[i] if labels and i < len(labels) else None
            account_tags = tags[i] if tags and i < len(tags) else []

            try:
                self.db.add_blockchain_account(
                    blockchain=blockchain.value,
                    account=account,
                )
                added.append(account)
            except Exception:
                # Account might already exist
                continue

        return added

    def remove_blockchain_accounts(
        self,
        blockchain: str,
        accounts: list[str],
    ) -> int:
        """Remove blockchain accounts"""
        # In real implementation, would delete from database
        return len(accounts)

    def get_evm_transactions(
        self,
        chain_id: int | None = None,
        address: ChecksumEvmAddress | None = None,
        from_timestamp: int = 0,
        to_timestamp: int = 2147483647,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get EVM transactions with filtering"""
        # Simplified implementation - would query from database
        transactions = []

        # Mock transaction data
        if address:
            transactions.append({
                'tx_hash': '0x123...',
                'chain_id': chain_id or 1,
                'timestamp': 1234567890,
                'from_address': address,
                'to_address': '0xabc...',
                'value': '1000000000000000000',
                'gas_used': '21000',
                'gas_price': '20000000000',
                'input_data': '0x',
                'nonce': 0,
            })

        return transactions[offset:offset + limit]

    def decode_pending_transactions(
        self,
        chain_id: int,
        tx_hashes: list[str],
    ) -> dict[str, Any]:
        """Decode pending EVM transactions"""
        results = {}

        for tx_hash in tx_hashes:
            # In real implementation, would fetch and decode transaction
            results[tx_hash] = {
                'decoded': True,
                'label': 'Token Transfer',
                'details': {
                    'from': '0x123...',
                    'to': '0xabc...',
                    'token': 'USDC',
                    'amount': '100.0',
                },
            }

        return results
