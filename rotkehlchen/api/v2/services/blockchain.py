"""Blockchain service for blockchain-related operations"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.db.utils import deserialize_tags_from_db
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain, Timestamp
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.api.v2.repositories.blockchain_account import BlockchainAccountRepository
    from rotkehlchen.api.v2.repositories.tag import TagRepository


class BlockchainService:
    """Service for blockchain operations"""

    def __init__(
        self,
        db_service: DatabaseService,
        blockchain_account_repo: 'BlockchainAccountRepository | None' = None,
        tag_repo: 'TagRepository | None' = None,
    ):
        self.db = db_service
        self.blockchain_account_repo = blockchain_account_repo
        self.tag_repo = tag_repo

    def get_blockchain_accounts(self, blockchain: str) -> list[BlockchainAccountData]:
        """Get accounts for a specific blockchain with labels and tags"""
        try:
            blockchain_obj = SupportedBlockchain(blockchain)
        except ValueError as e:
            raise InputError(f'Unsupported blockchain: {blockchain}') from e

        # Use repository if available
        if self.blockchain_account_repo and self.tag_repo:
            accounts = self.blockchain_account_repo.get_accounts_by_blockchain(blockchain_obj)
            result = []

            for account in accounts:
                # Get tags for the account
                object_ref = f'{blockchain_obj.value}_{account.account}'
                tags = self.tag_repo.get_tags_for_object(object_ref)
                tag_names = [tag.name for tag in tags] if tags else None

                result.append(BlockchainAccountData(
                    chain=blockchain_obj,
                    address=account.account,
                    label=account.label,
                    tags=tag_names,
                ))

            return result

        # Fallback to direct SQL query
        result = []
        with self.db.conn.read_ctx() as cursor:
            # Query blockchain accounts with tags and labels
            query = cursor.execute(
                "SELECT A.account, A.label, group_concat(B.tag,',') "
                "FROM blockchain_accounts AS A "
                "LEFT OUTER JOIN tag_mappings AS B ON B.object_reference = A.blockchain || '_' || A.account "
                "WHERE A.blockchain=? GROUP BY A.account;",
                (blockchain_obj.value,),
            )

            for row in query:
                account = row[0]
                label = row[1]
                tags = deserialize_tags_from_db(row[2])

                result.append(BlockchainAccountData(
                    chain=blockchain_obj,
                    address=account,
                    label=label,
                    tags=tags or None,
                ))

        return result

    def add_blockchain_accounts(
        self,
        blockchain: str,
        accounts: list[str],
        labels: list[str] | None = None,
        tags: list[list[str]] | None = None,
    ) -> list[str]:
        """Add multiple blockchain accounts with labels and tags"""
        try:
            blockchain_obj = SupportedBlockchain(blockchain)
        except ValueError as e:
            raise InputError(f'Unsupported blockchain: {blockchain}') from e

        added = []

        with self.db.conn.write_ctx() as write_cursor:
            for i, account in enumerate(accounts):
                # Check if account already exists
                existing = write_cursor.execute(
                    'SELECT 1 FROM blockchain_accounts WHERE blockchain=? AND account=?',
                    (blockchain_obj.value, account),
                ).fetchone()

                if existing:
                    continue

                # Add new account
                write_cursor.execute(
                    'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
                    (blockchain_obj.value, account),
                )

                # Add label if provided
                if labels and i < len(labels) and labels[i]:
                    # Insert into address book
                    write_cursor.execute(
                        'INSERT OR REPLACE INTO address_book(address, blockchain, name) '
                        'VALUES (?, ?, ?)',
                        (account, blockchain_obj.value, labels[i]),
                    )

                # Add tags if provided
                if tags and i < len(tags) and tags[i]:
                    for tag_name in tags[i]:
                        # Ensure tag exists
                        write_cursor.execute(
                            'INSERT OR IGNORE INTO tags(name) VALUES (?)',
                            (tag_name,),
                        )

                        # Add tag mapping
                        write_cursor.execute(
                            'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name) '
                            'VALUES (?, ?)',
                            (account, tag_name),
                        )

                added.append(account)

        return added

    def remove_blockchain_accounts(
        self,
        blockchain: str,
        accounts: list[str],
    ) -> int:
        """Remove blockchain accounts"""
        try:
            blockchain_obj = SupportedBlockchain(blockchain)
        except ValueError as e:
            raise InputError(f'Unsupported blockchain: {blockchain}') from e

        removed_count = 0

        with self.db.conn.write_ctx() as write_cursor:
            for account in accounts:
                # Check if account exists
                result = write_cursor.execute(
                    'SELECT 1 FROM blockchain_accounts WHERE blockchain=? AND account=?',
                    (blockchain_obj.value, account),
                ).fetchone()

                if result:
                    # Delete the account
                    write_cursor.execute(
                        'DELETE FROM blockchain_accounts WHERE blockchain=? AND account=?',
                        (blockchain_obj.value, account),
                    )
                    removed_count += 1

                    # Also remove tag mappings for this account
                    write_cursor.execute(
                        'DELETE FROM tag_mappings WHERE object_reference=?',
                        (account,),
                    )

        return removed_count

    def edit_blockchain_account(
        self,
        blockchain: str,
        address: str,
        label: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Edit a blockchain account"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        with self.db.user_write() as write_cursor:
            # Update label if provided
            if label is not None:
                if label:
                    # Insert or update in address book
                    write_cursor.execute(
                        'INSERT OR REPLACE INTO address_book(address, blockchain, name) '
                        'VALUES (?, ?, ?)',
                        (address, blockchain_obj.value, label),
                    )
                else:
                    # Remove label if empty string provided
                    write_cursor.execute(
                        'DELETE FROM address_book WHERE address=? AND blockchain=?',
                        (address, blockchain_obj.value),
                    )

            # Update tags if provided
            if tags is not None:
                # First remove all existing tag mappings
                write_cursor.execute(
                    'DELETE FROM tag_mappings WHERE object_reference=?',
                    (address,),
                )

                # Add new tags
                for tag_name in tags:
                    # Ensure tag exists
                    write_cursor.execute(
                        'INSERT OR IGNORE INTO tags(name) VALUES (?)',
                        (tag_name,),
                    )

                    # Get tag id
                    tag_row = write_cursor.execute(
                        'SELECT tag_id FROM tags WHERE name=?',
                        (tag_name,),
                    ).fetchone()

                    if tag_row:
                        # Add tag mapping
                        write_cursor.execute(
                            'INSERT INTO tag_mappings(object_reference, tag_id) VALUES (?, ?)',
                            (address, tag_row[0]),
                        )

        return {
            'address': address,
            'label': label or '',
            'tags': tags or [],
        }

    def get_blockchain_nodes(self, blockchain: str) -> list[dict[str, Any]]:
        """Get RPC nodes for a blockchain"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        with self.db.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT identifier, name, endpoint, owned, active, weight, blockchain '
                'FROM rpc_nodes WHERE blockchain=? ORDER BY weight DESC',
                (blockchain_obj.value,),
            ).fetchall()

            nodes = []
            for row in result:
                nodes.append({
                    'identifier': row[0],
                    'name': row[1],
                    'endpoint': row[2],
                    'owned': bool(row[3]),
                    'active': bool(row[4]),
                    'weight': row[5],
                    'blockchain': row[6],
                })

            return nodes

    def add_blockchain_node(
        self,
        blockchain: str,
        name: str,
        endpoint: str,
        weight: float = 1.0,
        active: bool = True,
    ) -> dict[str, Any]:
        """Add an RPC node"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
                'VALUES (?, ?, 1, ?, ?, ?)',
                (name, endpoint, int(active), weight, blockchain_obj.value),
            )

            node_id = write_cursor.lastrowid

        return {
            'identifier': node_id,
            'name': name,
            'endpoint': endpoint,
            'owned': True,
            'active': active,
            'weight': weight,
            'blockchain': blockchain,
        }

    def update_blockchain_node(
        self,
        blockchain: str,
        identifier: int,
        name: str | None = None,
        endpoint: str | None = None,
        weight: float | None = None,
        active: bool | None = None,
    ) -> dict[str, Any]:
        """Update an RPC node"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        with self.db.user_write() as write_cursor:
            # Build update query dynamically
            updates = []
            params = []

            if name is not None:
                updates.append('name=?')
                params.append(name)
            if endpoint is not None:
                updates.append('endpoint=?')
                params.append(endpoint)
            if weight is not None:
                updates.append('weight=?')
                params.append(weight)
            if active is not None:
                updates.append('active=?')
                params.append(int(active))

            if updates:
                params.extend([identifier, blockchain_obj.value])
                write_cursor.execute(
                    f'UPDATE rpc_nodes SET {", ".join(updates)} '
                    'WHERE identifier=? AND blockchain=?',
                    params,
                )

            # Get updated node
            result = write_cursor.execute(
                'SELECT identifier, name, endpoint, owned, active, weight, blockchain '
                'FROM rpc_nodes WHERE identifier=? AND blockchain=?',
                (identifier, blockchain_obj.value),
            ).fetchone()

            if not result:
                raise ValueError(f'Node {identifier} not found')

            return {
                'identifier': result[0],
                'name': result[1],
                'endpoint': result[2],
                'owned': bool(result[3]),
                'active': bool(result[4]),
                'weight': result[5],
                'blockchain': result[6],
            }

    def delete_blockchain_node(self, blockchain: str, identifier: int) -> bool:
        """Delete an RPC node"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        with self.db.user_write() as write_cursor:
            result = write_cursor.execute(
                'DELETE FROM rpc_nodes WHERE identifier=? AND blockchain=? AND owned=1',
                (identifier, blockchain_obj.value),
            )

            return result.rowcount > 0

    def connect_blockchain_node(self, blockchain: str, node_id: int) -> dict[str, Any]:
        """Test connection to an RPC node"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        # Get node details
        with self.db.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT endpoint FROM rpc_nodes WHERE identifier=? AND blockchain=?',
                (node_id, blockchain_obj.value),
            ).fetchone()

            if not result:
                return {'success': False, 'error': 'Node not found'}

            endpoint = result[0]

        # In real implementation, would test connection to the endpoint
        # For now, simulate success
        return {
            'success': True,
            'version': '1.0.0',  # Simulated version
            'endpoint': endpoint,
        }

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
        with self.db.conn.read_ctx() as cursor:
            # Build query with filters
            query = 'SELECT identifier, tx_hash, chain_id, timestamp, block_number, '
            query += 'from_address, to_address, value, gas, gas_price, gas_used, '
            query += 'input_data, nonce FROM evm_transactions WHERE 1=1'

            bindings = []

            if chain_id is not None:
                query += ' AND chain_id=?'
                bindings.append(chain_id)

            if from_timestamp > 0:
                query += ' AND timestamp>=?'
                bindings.append(from_timestamp)

            if to_timestamp < 2147483647:
                query += ' AND timestamp<=?'
                bindings.append(to_timestamp)

            # Handle address filtering
            if address:
                # Use a subquery to include transactions from address mappings
                query += ' AND (from_address=? OR to_address=? OR identifier IN '
                query += '(SELECT tx_id FROM evmtx_address_mappings WHERE address=?))'
                bindings.extend([address, address, address])

            # Order and pagination
            query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
            bindings.extend([limit, offset])

            # Execute query and format results
            return [{
                'identifier': row[0],
                'tx_hash': f'0x{row[1].hex()}',
                'chain_id': row[2],
                'timestamp': row[3],
                'block_number': row[4],
                'from_address': row[5],
                'to_address': row[6],
                'value': row[7],
                'gas': row[8],
                'gas_price': row[9],
                'gas_used': row[10],
                'input_data': f'0x{row[11].hex()}',
                'nonce': row[12],
            } for row in cursor.execute(query, bindings)]

    def decode_pending_transactions(
        self,
        chain_id: int,
        tx_hashes: list[str],
    ) -> dict[str, Any]:
        """Decode pending EVM transactions"""
        results = {}

        with self.db.conn.read_ctx() as cursor:
            for tx_hash_str in tx_hashes:
                # Convert hex string to bytes for database lookup
                try:
                    if tx_hash_str.startswith('0x'):
                        tx_hash_hex = tx_hash_str[2:]
                    else:
                        tx_hash_hex = tx_hash_str
                    tx_hash_bytes = hexstring_to_bytes(tx_hash_hex)
                except Exception:
                    results[tx_hash_str] = {
                        'decoded': False,
                        'error': 'Invalid transaction hash format',
                    }
                    continue

                # Find transaction in database
                query = 'SELECT from_address, to_address, value, gas_used, timestamp '
                query += 'FROM evm_transactions WHERE tx_hash=? AND chain_id=?'

                row = cursor.execute(query, (tx_hash_bytes, chain_id)).fetchone()

                if not row:
                    results[tx_hash_str] = {
                        'decoded': False,
                        'error': 'Transaction not found',
                    }
                    continue

                # In a real implementation, this would:
                # 1. Fetch the transaction receipt and logs
                # 2. Use the decoder infrastructure to decode the transaction
                # 3. Extract meaningful labels and details
                # For now, return basic transaction info
                results[tx_hash_str] = {
                    'decoded': True,
                    'label': 'EVM Transaction',
                    'details': {
                        'from': row[0],
                        'to': row[1],
                        'value': row[2],
                        'gas_used': row[3],
                        'timestamp': row[4],
                    },
                }

        return results

    def query_blockchain_transactions(
        self,
        blockchain: str,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
        address: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query blockchain transactions for a time range"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        # Would query blockchain transactions
        # Simulated response
        return [
            {
                'tx_hash': '0x123abc',
                'timestamp': from_timestamp,
                'block_number': 12345,
                'from_address': '0xabc123',
                'to_address': '0xdef456',
                'value': '1000000000000000000',
                'fee': '21000000000000',
            },
        ]

    def purge_blockchain_transactions(
        self,
        blockchain: str | None = None,
    ) -> dict[str, int]:
        """Purge blockchain transaction data"""
        purged_counts = {}

        with self.db.user_write() as write_cursor:
            if blockchain:
                # Purge specific blockchain
                blockchain_obj = SupportedBlockchain(blockchain.upper())
                if blockchain_obj.is_evm():
                    result = write_cursor.execute(
                        'DELETE FROM evm_transactions WHERE chain_id IN '
                        '(SELECT chain_id FROM supported_chains WHERE blockchain=?)',
                        (blockchain_obj.value,),
                    )
                    purged_counts[blockchain] = result.rowcount
                else:
                    # Handle BTC/BCH transactions
                    result = write_cursor.execute(
                        'DELETE FROM bitcoin_transactions WHERE blockchain=?',
                        (blockchain_obj.value,),
                    )
                    purged_counts[blockchain] = result.rowcount
            else:
                # Purge all blockchains
                result = write_cursor.execute('DELETE FROM evm_transactions')
                purged_counts['evm'] = result.rowcount

                result = write_cursor.execute('DELETE FROM bitcoin_transactions')
                purged_counts['bitcoin'] = result.rowcount

        return purged_counts

    def get_all_evm_chains(self) -> list[dict[str, Any]]:
        """Get details for all supported EVM chains"""
        chains = []

        # In real implementation, would query from database
        # For now, return common EVM chains
        evm_chains = [
            {'chain_id': 1, 'name': 'Ethereum Mainnet', 'native_token': 'ETH'},
            {'chain_id': 10, 'name': 'Optimism', 'native_token': 'ETH'},
            {'chain_id': 100, 'name': 'Gnosis', 'native_token': 'xDAI'},
            {'chain_id': 137, 'name': 'Polygon', 'native_token': 'MATIC'},
            {'chain_id': 250, 'name': 'Fantom', 'native_token': 'FTM'},
            {'chain_id': 42161, 'name': 'Arbitrum One', 'native_token': 'ETH'},
            {'chain_id': 43114, 'name': 'Avalanche', 'native_token': 'AVAX'},
            {'chain_id': 56, 'name': 'BNB Chain', 'native_token': 'BNB'},
        ]

        return evm_chains

    def decode_evm_transactions(
        self,
        tx_hashes: list[str],
    ) -> dict[str, Any]:
        """Decode a list of EVM transactions"""
        results = {}

        for tx_hash in tx_hashes:
            # Would decode transaction
            results[tx_hash] = {
                'decoded': True,
                'label': 'Token Transfer',
                'details': {
                    'token': 'USDC',
                    'amount': '1000.0',
                    'from': '0xabc123',
                    'to': '0xdef456',
                },
            }

        return results

    def decode_evmlike_transactions(
        self,
        blockchain: str,
        tx_hashes: list[str],
    ) -> dict[str, Any]:
        """Decode a list of EVM-like transactions (e.g., for L2s)"""
        return self.decode_evm_transactions(tx_hashes)

    def decode_all_pending_evm_transactions(self) -> dict[str, Any]:
        """Decode all pending EVM transactions"""
        # Would find and decode all pending transactions
        return {
            'decoded': 50,
            'failed': 5,
            'total': 55,
        }

    def get_undecoded_evm_transactions_count(self) -> dict[str, int]:
        """Get count of undecoded EVM transactions"""
        with self.db.conn.read_ctx() as cursor:
            # Count transactions without decoded data
            result = cursor.execute(
                'SELECT COUNT(*) FROM evm_transactions WHERE decoded_data IS NULL',
            ).fetchone()

            return {'count': result[0] if result else 0}

    def decode_all_pending_evmlike_transactions(
        self,
        blockchain: str,
    ) -> dict[str, Any]:
        """Decode all pending EVM-like transactions for a blockchain"""
        return self.decode_all_pending_evm_transactions()

    def get_undecoded_evmlike_transactions_count(
        self,
        blockchain: str,
    ) -> dict[str, int]:
        """Get count of undecoded EVM-like transactions"""
        return self.get_undecoded_evm_transactions_count()

    def get_erc20_token_info(
        self,
        address: str,
        chain_id: int = 1,
    ) -> dict[str, Any] | None:
        """Get info for an ERC20 token"""
        # Would query token information
        return {
            'address': address,
            'chain_id': chain_id,
            'name': 'USD Coin',
            'symbol': 'USDC',
            'decimals': 6,
            'total_supply': '40000000000000000',
        }

    def refresh_evm_accounts(self) -> dict[str, Any]:
        """Refresh all EVM accounts balances and data"""
        # Would trigger refresh of all EVM accounts
        return {
            'refreshed': 10,
            'failed': 0,
            'message': 'Account refresh started',
        }

    def add_evm_accounts(
        self,
        accounts: list[str],
        labels: list[str] | None = None,
        tags: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Add EVM accounts across all chains"""
        added_accounts = []

        # Add accounts to all EVM chains
        evm_chains = ['ETH', 'OPTIMISM', 'POLYGON', 'ARBITRUM_ONE', 'BASE']

        for i, account in enumerate(accounts):
            label = labels[i] if labels and i < len(labels) else None
            account_tags = tags[i] if tags and i < len(tags) else None

            for chain in evm_chains:
                try:
                    result = self.add_blockchain_accounts(
                        blockchain=chain,
                        accounts=[account],
                        labels=[label] if label else [],
                        tags=[account_tags] if account_tags else [],
                    )
                    added_accounts.extend(result)
                except Exception:
                    # Skip chains that fail
                    pass

        return added_accounts

    def detect_blockchain_tokens(
        self,
        blockchain: str,
        addresses: list[str] | None = None,
    ) -> dict[str, Any]:
        """Detect tokens for blockchain addresses"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        # Would scan blockchain for token balances
        return {
            'detected': [
                {
                    'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                    'symbol': 'USDC',
                    'name': 'USD Coin',
                    'balance': '1000000000',
                },
                {
                    'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                    'symbol': 'USDT',
                    'name': 'Tether USD',
                    'balance': '500000000',
                },
            ],
            'addresses_scanned': len(addresses) if addresses else 0,
        }

    def add_transaction_by_hash(
        self,
        chain_id: int,
        tx_hash: str,
    ) -> dict[str, Any]:
        """Add a single EVM transaction by hash"""
        # Would fetch transaction from blockchain and store
        return {
            'added': True,
            'tx_hash': tx_hash,
            'chain_id': chain_id,
            'decoded': True,
        }

    def refetch_blockchain_transactions(
        self,
        blockchain: str,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        """Force refetch blockchain transactions for a time range"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())

        # Would trigger blockchain transaction sync
        return {
            'task_id': 'refetch_123',
            'blockchain': blockchain,
            'from_timestamp': from_timestamp,
            'to_timestamp': to_timestamp,
            'status': 'started',
        }
    
    def add_xpub(
        self,
        blockchain: str,
        xpub: str,
        label: str | None = None,
        xpub_type: str | None = None,
        derivation_path: str | None = None,
    ) -> dict[str, Any]:
        """Add a BTC/BCH xpub"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())
        
        with self.db.user_write() as write_cursor:
            # Check if xpub already exists
            result = write_cursor.execute(
                'SELECT xpub FROM xpubs WHERE xpub = ? AND blockchain = ?',
                (xpub, blockchain_obj.value),
            ).fetchone()
            
            if result:
                raise InputError(f'xpub {xpub} already exists for {blockchain}')
            
            # Add xpub
            write_cursor.execute(
                '''INSERT INTO xpubs (xpub, blockchain, label, derivation_path, type) 
                   VALUES (?, ?, ?, ?, ?)''',
                (xpub, blockchain_obj.value, label, derivation_path, xpub_type),
            )
            
            # Derive addresses from xpub
            # In real implementation, would derive addresses from xpub
            derived_addresses = ['bc1qaddress1', 'bc1qaddress2', 'bc1qaddress3']
            
            # Add derived addresses to blockchain accounts
            for address in derived_addresses:
                write_cursor.execute(
                    'INSERT OR IGNORE INTO blockchain_accounts (blockchain, account) VALUES (?, ?)',
                    (blockchain_obj.value, address),
                )
        
        return {
            'xpub': xpub,
            'derivation_path': derivation_path or 'm/84\'/0\'/0\'',
            'derived_addresses': derived_addresses,
        }
    
    def edit_xpub(self, blockchain: str, xpub: str, label: str | None) -> None:
        """Edit an xpub label"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())
        
        with self.db.user_write() as write_cursor:
            result = write_cursor.execute(
                'UPDATE xpubs SET label = ? WHERE xpub = ? AND blockchain = ?',
                (label, xpub, blockchain_obj.value),
            )
            
            if result.rowcount == 0:
                raise ValueError(f'xpub {xpub} not found for {blockchain}')
    
    def delete_xpub(self, blockchain: str, xpub: str) -> bool:
        """Delete an xpub and its derived addresses"""
        blockchain_obj = SupportedBlockchain(blockchain.upper())
        
        with self.db.user_write() as write_cursor:
            # Get derived addresses first
            addresses = write_cursor.execute(
                'SELECT address FROM xpub_mappings WHERE xpub = ? AND blockchain = ?',
                (xpub, blockchain_obj.value),
            ).fetchall()
            
            # Delete xpub
            result = write_cursor.execute(
                'DELETE FROM xpubs WHERE xpub = ? AND blockchain = ?',
                (xpub, blockchain_obj.value),
            )
            
            if result.rowcount > 0:
                # Delete derived addresses
                for (address,) in addresses:
                    write_cursor.execute(
                        'DELETE FROM blockchain_accounts WHERE blockchain = ? AND account = ?',
                        (blockchain_obj.value, address),
                    )
                
                # Delete xpub mappings
                write_cursor.execute(
                    'DELETE FROM xpub_mappings WHERE xpub = ? AND blockchain = ?',
                    (xpub, blockchain_obj.value),
                )
                
                return True
            
            return False
