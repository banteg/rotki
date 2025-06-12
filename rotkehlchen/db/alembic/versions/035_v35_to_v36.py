"""Upgrade from v35 to v36

Revision ID: 035_v35_to_v36
Revises: 034_v34_to_v35
Create Date: 2025-01-06

This upgrade includes:
- Remove adex data and tables
- Upgrade ignored actions ids for transactions
- Upgrade accounts details table to add chain id
- Rename all eth tables to evm and add chain id
- Upgrade history_events_mappings to have key/value schema
- Upgrade nfts table to add image url, collection name
- Rename web3_nodes to rpc_nodes
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '035_v35_to_v36'
down_revision = '034_v34_to_v35'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v35 to v36"""
    
    # Remove adex data
    op.drop_table('adex_events')
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'adex\\_events%' ESCAPE '\\'")
    
    # Update active modules - remove adex
    op.execute("""
        UPDATE settings 
        SET value = REPLACE(value, ',"adex"', '') 
        WHERE name='active_modules' AND value LIKE '%"adex"%'
    """)
    
    # Update ignored actions for transactions
    op.execute("UPDATE ignored_actions SET identifier = '1' || identifier WHERE type='C'")
    
    # Create new evm_accounts_details table (replacing accounts_details)
    op.create_table('evm_accounts_details',
        sa.Column('account', sa.TEXT, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('key', sa.TEXT, nullable=False),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.PrimaryKeyConstraint('account', 'chain_id', 'key')
    )
    
    # Migrate data from accounts_details
    op.execute("""
        INSERT INTO evm_accounts_details (account, chain_id, key, value)
        SELECT account, 1, key, value FROM accounts_details
        WHERE blockchain = 'ETH'
    """)
    
    op.drop_table('accounts_details')
    
    # Rename ethereum tables to evm tables and add chain_id
    
    # Create new evm_transactions table
    op.create_table('evm_transactions',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('block_number', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.Column('gas', sa.TEXT, nullable=False),
        sa.Column('gas_price', sa.TEXT, nullable=False),
        sa.Column('gas_used', sa.TEXT, nullable=False),
        sa.Column('input_data', sa.BLOB, nullable=False),
        sa.Column('nonce', sa.INTEGER, nullable=False),
        sa.PrimaryKeyConstraint('tx_hash', 'chain_id')
    )
    
    # Copy data from ethereum_transactions
    op.execute("""
        INSERT INTO evm_transactions 
        SELECT tx_hash, 1, timestamp, block_number, from_address, to_address, 
               value, gas, gas_price, gas_used, input_data, nonce
        FROM ethereum_transactions
    """)
    
    op.drop_table('ethereum_transactions')
    
    # Create new evm_internal_transactions table
    op.create_table('evm_internal_transactions',
        sa.Column('parent_tx_hash', sa.BLOB, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('trace_id', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('block_number', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['parent_tx_hash', 'chain_id'], ['evm_transactions.tx_hash', 'evm_transactions.chain_id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('parent_tx_hash', 'chain_id', 'trace_id', 'from_address', 'to_address', 'value')
    )
    
    # Copy data from ethereum_internal_transactions
    op.execute("""
        INSERT INTO evm_internal_transactions 
        SELECT parent_tx_hash, 1, trace_id, 0, 0, from_address, to_address, value
        FROM ethereum_internal_transactions
    """)
    
    op.drop_table('ethereum_internal_transactions')
    
    # Create and migrate evmtx_receipts
    op.create_table('evmtx_receipts',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('contract_address', sa.TEXT),
        sa.Column('status', sa.INTEGER, nullable=False),
        sa.Column('type', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash', 'chain_id'], ['evm_transactions.tx_hash', 'evm_transactions.chain_id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'chain_id')
    )
    
    op.execute("""
        INSERT INTO evmtx_receipts 
        SELECT tx_hash, 1, contract_address, status, type
        FROM ethtx_receipts
    """)
    
    op.drop_table('ethtx_receipts')
    
    # Create and migrate evmtx_receipt_logs
    op.create_table('evmtx_receipt_logs',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('data', sa.BLOB, nullable=False),
        sa.Column('address', sa.TEXT, nullable=False),
        sa.Column('removed', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash', 'chain_id'], ['evmtx_receipts.tx_hash', 'evmtx_receipts.chain_id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'chain_id', 'log_index')
    )
    
    op.execute("""
        INSERT INTO evmtx_receipt_logs 
        SELECT tx_hash, 1, log_index, data, address, removed
        FROM ethtx_receipt_logs
    """)
    
    op.drop_table('ethtx_receipt_logs')
    
    # Create and migrate evmtx_receipt_log_topics
    op.create_table('evmtx_receipt_log_topics',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('topic', sa.BLOB, nullable=False),
        sa.Column('topic_index', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash', 'chain_id', 'log_index'], ['evmtx_receipt_logs.tx_hash', 'evmtx_receipt_logs.chain_id', 'evmtx_receipt_logs.log_index'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'chain_id', 'log_index', 'topic_index')
    )
    
    op.execute("""
        INSERT INTO evmtx_receipt_log_topics 
        SELECT tx_hash, 1, log_index, topic, topic_index
        FROM ethtx_receipt_log_topics
    """)
    
    op.drop_table('ethtx_receipt_log_topics')
    
    # Create and migrate evmtx_address_mappings
    op.create_table('evmtx_address_mappings',
        sa.Column('address', sa.TEXT, nullable=False),
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('blockchain', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash', 'chain_id'], ['evm_transactions.tx_hash', 'evm_transactions.chain_id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('address', 'tx_hash', 'chain_id')
    )
    
    op.execute("""
        INSERT INTO evmtx_address_mappings 
        SELECT address, tx_hash, 1, 1
        FROM ethtx_address_mappings
    """)
    
    op.drop_table('ethtx_address_mappings')
    
    # Update evm_tx_mappings to add chain_id
    op.execute("""
        CREATE TABLE evm_tx_mappings_new (
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            value INTEGER NOT NULL,
            FOREIGN KEY(tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY (tx_hash, chain_id, value)
        )
    """)
    
    op.execute("""
        INSERT INTO evm_tx_mappings_new 
        SELECT tx_hash, 1, value FROM evm_tx_mappings
    """)
    
    op.drop_table('evm_tx_mappings')
    op.execute("ALTER TABLE evm_tx_mappings_new RENAME TO evm_tx_mappings")
    
    # Update history_events_mappings
    op.execute("""
        CREATE TABLE history_events_mappings_new (
            parent_identifier INTEGER NOT NULL,
            name TEXT NOT NULL,
            value INTEGER NOT NULL,
            FOREIGN KEY(parent_identifier) REFERENCES history_events(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY (parent_identifier, name, value)
        )
    """)
    
    # Migrate data - only keep customized mappings
    op.execute("""
        INSERT INTO history_events_mappings_new (parent_identifier, name, value)
        SELECT parent_identifier, 'customized', 1
        FROM history_events_mappings 
        WHERE value = 'customized'
    """)
    
    op.drop_table('history_events_mappings')
    op.execute("ALTER TABLE history_events_mappings_new RENAME TO history_events_mappings")
    
    # Update nfts table
    op.drop_table('nfts')
    op.create_table('nfts',
        sa.Column('identifier', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('name', sa.TEXT),
        sa.Column('last_price', sa.TEXT),
        sa.Column('last_price_asset', sa.TEXT),
        sa.Column('manual_price', sa.INTEGER, nullable=False, server_default='1'),
        sa.Column('owner_address', sa.TEXT),
        sa.Column('blockchain', sa.CHAR(1)),
        sa.Column('is_lp', sa.INTEGER, nullable=False, server_default='0'),
        sa.Column('image_url', sa.TEXT),
        sa.Column('collection_name', sa.TEXT),
        sa.ForeignKeyConstraint(['identifier'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['last_price_asset'], ['assets.identifier'], onupdate='CASCADE')
    )
    
    # Rename web3_nodes to rpc_nodes
    op.create_table('rpc_nodes',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('name', sa.TEXT, nullable=False),
        sa.Column('endpoint', sa.TEXT, nullable=False),
        sa.Column('owned', sa.INTEGER, nullable=False),
        sa.Column('active', sa.INTEGER, nullable=False),
        sa.Column('weight', sa.TEXT, nullable=False),
        sa.Column('blockchain', sa.TEXT, nullable=False),
        sa.UniqueConstraint('endpoint', 'blockchain')
    )
    
    # Migrate data from web3_nodes
    op.execute("""
        INSERT INTO rpc_nodes (name, endpoint, owned, active, weight, blockchain)
        SELECT name, endpoint, owned, active, weight, 'ETH' FROM web3_nodes
    """)
    
    op.drop_table('web3_nodes')
    
    # Update blockchain accounts with tags
    op.execute("""
        DELETE FROM tag_mappings 
        WHERE object_reference IN (
            SELECT account FROM blockchain_accounts WHERE blockchain = 'ETH'
        )
    """)
    
    # Drop eth_tokens table if exists
    op.execute("DROP TABLE IF EXISTS eth_tokens")
    
    # Add new location for Gitcoin (from v31_v32 migration)
    op.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('^', 30)")
    
    # Fix eth2 daily staking details - correct PnL calculation
    op.execute("""
        UPDATE eth2_daily_staking_details 
        SET pnl = CAST(pnl AS REAL) / 1000000000.0
        WHERE timestamp = 1606780800
    """)


def downgrade() -> None:
    """Downgrade from v36 to v35"""
    raise NotImplementedError("Downgrade not implemented for this migration")