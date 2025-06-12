"""Tests for the V2 blockchain service"""
import pytest

from rotkehlchen.api.v2.services.blockchain import BlockchainService
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.fixture
def blockchain_service(database):
    """Create a blockchain service instance"""
    # Use the database connection from DBHandler
    db_service = DatabaseService(database.conn)
    service = BlockchainService(db_service)
    
    # Clean up all blockchain accounts to start fresh
    with database.conn.write_ctx() as cursor:
        cursor.execute("DELETE FROM tag_mappings")
        cursor.execute("DELETE FROM blockchain_accounts")
        cursor.execute("DELETE FROM address_book")
    
    return service


def test_get_blockchain_accounts_empty(blockchain_service):
    """Test getting blockchain accounts when none exist"""
    accounts = blockchain_service.get_blockchain_accounts('ETH')
    assert accounts == []


def test_add_and_get_blockchain_accounts(blockchain_service):
    """Test adding and retrieving blockchain accounts"""
    # Add accounts
    addresses = [
        '0x1234567890123456789012345678901234567890',
        '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
    ]
    added = blockchain_service.add_blockchain_accounts(
        blockchain='ETH',
        accounts=addresses,
    )
    
    assert len(added) == 2
    assert set(added) == set(addresses)
    
    # Get accounts
    accounts = blockchain_service.get_blockchain_accounts('ETH')
    assert len(accounts) == 2
    
    # Check account data
    account_addresses = [acc.address for acc in accounts]
    assert set(account_addresses) == set(addresses)
    
    for account in accounts:
        assert account.chain == SupportedBlockchain.ETHEREUM
        assert account.label is None
        assert account.tags is None


def test_add_blockchain_accounts_with_tags(blockchain_service):
    """Test adding blockchain accounts with tags"""
    # First create tags using raw SQL
    with blockchain_service.db.connection.write_ctx() as cursor:
        cursor.execute("INSERT INTO tags(name, description) VALUES (?, ?)", ('defi', 'DeFi accounts'))
        cursor.execute("INSERT INTO tags(name, description) VALUES (?, ?)", ('personal', 'Personal accounts'))
    
    # Add accounts with tags
    addresses = [
        '0x1111111111111111111111111111111111111111',
        '0x2222222222222222222222222222222222222222',
    ]
    tags = [
        ['defi', 'personal'],
        ['defi'],
    ]
    
    added = blockchain_service.add_blockchain_accounts(
        blockchain='ETH',
        accounts=addresses,
        tags=tags,
    )
    
    assert len(added) == 2
    
    # Get accounts and check tags
    accounts = blockchain_service.get_blockchain_accounts('ETH')
    assert len(accounts) == 2
    
    # Sort accounts by address for consistent testing
    accounts.sort(key=lambda x: x.address)
    
    assert accounts[0].address == addresses[0]
    assert set(accounts[0].tags) == {'defi', 'personal'}
    
    assert accounts[1].address == addresses[1]
    assert accounts[1].tags == ['defi']


def test_remove_blockchain_accounts(blockchain_service):
    """Test removing blockchain accounts"""
    # Add accounts first
    addresses = [
        '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
        '0xcccccccccccccccccccccccccccccccccccccccc',
    ]
    blockchain_service.add_blockchain_accounts(
        blockchain='ETH',
        accounts=addresses,
    )
    
    # Remove two accounts
    removed_count = blockchain_service.remove_blockchain_accounts(
        blockchain='ETH',
        accounts=addresses[:2],
    )
    
    assert removed_count == 2
    
    # Check remaining accounts
    accounts = blockchain_service.get_blockchain_accounts('ETH')
    assert len(accounts) == 1
    assert accounts[0].address == addresses[2]


def test_get_evm_transactions_empty(blockchain_service):
    """Test getting EVM transactions when none exist"""
    transactions = blockchain_service.get_evm_transactions()
    assert transactions == []


def test_get_evm_transactions_with_data(blockchain_service):
    """Test getting EVM transactions with sample data"""
    # Insert sample transaction using raw SQL
    with blockchain_service.db.connection.write_ctx() as cursor:
        tx_hash = hexstring_to_bytes('1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')
        cursor.execute(
            """INSERT INTO evm_transactions(
                tx_hash, chain_id, timestamp, block_number, 
                from_address, to_address, value, gas, gas_price, 
                gas_used, input_data, nonce
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tx_hash,
                ChainID.ETHEREUM.value,
                1700000000,
                18000000,
                '0x1111111111111111111111111111111111111111',
                '0x2222222222222222222222222222222222222222',
                '1000000000000000000',  # 1 ETH
                '21000',
                '20000000000',  # 20 gwei
                '21000',
                b'',
                0,
            )
        )
    
    # Get all transactions
    transactions = blockchain_service.get_evm_transactions()
    assert len(transactions) == 1
    
    tx_data = transactions[0]
    assert tx_data['tx_hash'] == '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    assert tx_data['chain_id'] == ChainID.ETHEREUM.value
    assert tx_data['from_address'] == '0x1111111111111111111111111111111111111111'
    assert tx_data['to_address'] == '0x2222222222222222222222222222222222222222'
    assert tx_data['value'] == '1000000000000000000'
    
    # Test filtering by chain_id
    transactions = blockchain_service.get_evm_transactions(chain_id=ChainID.OPTIMISM.value)
    assert len(transactions) == 0
    
    # Test filtering by address
    transactions = blockchain_service.get_evm_transactions(
        address=ChecksumEvmAddress('0x1111111111111111111111111111111111111111')
    )
    assert len(transactions) == 1
    
    # Test pagination
    transactions = blockchain_service.get_evm_transactions(limit=1, offset=1)
    assert len(transactions) == 0


def test_decode_pending_transactions(blockchain_service):
    """Test decoding pending transactions"""
    # Insert a transaction
    tx_hash = '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef'
    with blockchain_service.db.connection.write_ctx() as cursor:
        cursor.execute(
            """INSERT INTO evm_transactions(
                tx_hash, chain_id, timestamp, block_number, 
                from_address, to_address, value, gas, gas_price, 
                gas_used, input_data, nonce
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                hexstring_to_bytes(tx_hash[2:]),
                ChainID.ETHEREUM.value,
                1700000000,
                18000000,
                '0x3333333333333333333333333333333333333333',
                '0x4444444444444444444444444444444444444444',
                '500000000000000000',  # 0.5 ETH
                '100000',
                '30000000000',  # 30 gwei
                '75000',
                b'',
                5,
            )
        )
    
    # Decode the transaction
    results = blockchain_service.decode_pending_transactions(
        chain_id=ChainID.ETHEREUM.value,
        tx_hashes=[tx_hash],
    )
    
    assert len(results) == 1
    assert tx_hash in results
    
    decoded = results[tx_hash]
    assert decoded['decoded'] is True
    assert decoded['label'] == 'EVM Transaction'
    assert decoded['details']['from'] == '0x3333333333333333333333333333333333333333'
    assert decoded['details']['to'] == '0x4444444444444444444444444444444444444444'
    assert decoded['details']['value'] == '500000000000000000'
    
    # Test with non-existent transaction
    results = blockchain_service.decode_pending_transactions(
        chain_id=ChainID.ETHEREUM.value,
        tx_hashes=['0xnonexistent'],
    )
    
    assert results['0xnonexistent']['decoded'] is False
    assert 'error' in results['0xnonexistent']


def test_multiple_blockchain_support(blockchain_service):
    """Test support for multiple blockchains"""
    # Add Ethereum accounts
    eth_addresses = [
        '0xe1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1',
        '0xe2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2e2',
    ]
    blockchain_service.add_blockchain_accounts(
        blockchain='ETH',
        accounts=eth_addresses,
    )
    
    # Add Optimism accounts
    opt_addresses = [
        '0xf1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1',
    ]
    blockchain_service.add_blockchain_accounts(
        blockchain='OPTIMISM',
        accounts=opt_addresses,
    )
    
    # Get Ethereum accounts
    eth_accounts = blockchain_service.get_blockchain_accounts('ETH')
    assert len(eth_accounts) == 2
    assert all(acc.chain == SupportedBlockchain.ETHEREUM for acc in eth_accounts)
    
    # Get Optimism accounts
    opt_accounts = blockchain_service.get_blockchain_accounts('OPTIMISM')
    assert len(opt_accounts) == 1
    assert all(acc.chain == SupportedBlockchain.OPTIMISM for acc in opt_accounts)