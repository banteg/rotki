"""Upgrade from v38 to v39

Revision ID: 038_v38_to_v39
Revises: 037_v37_to_v38
Create Date: 2025-01-06

This upgrade includes:
- Update NFT table to not use double quotes
- Reduce size of some event identifiers
- Primary key of evm tx tables becomes unique integer
- Reset all decoded events, except the customized ones
- Add Arbitrum One location and nodes
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '038_v38_to_v39'
down_revision = '037_v37_to_v38'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v38 to v39"""
    
    # Create optimism_transactions table (for tracking)
    op.create_table('optimism_transactions',
        sa.Column('tx_id', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('block_number', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.Column('gas', sa.TEXT, nullable=False),
        sa.Column('gas_price', sa.TEXT, nullable=False),
        sa.Column('gas_used', sa.TEXT, nullable=False),
        sa.Column('input_data', sa.BLOB, nullable=False),
        sa.Column('nonce', sa.INTEGER, nullable=False)
    )
    
    # Update event identifiers - replace rotki_events_ prefixes
    op.execute("""
        UPDATE history_events 
        SET event_identifier = REPLACE(event_identifier, 'rotki_events_', '')
        WHERE event_identifier LIKE 'rotki_events_%' ESCAPE '\\'
    """)
    
    # Update validator exits event identifiers
    op.execute("""
        UPDATE history_events h
        SET event_identifier = 'EXE' || s.validator_index || h.timestamp
        FROM eth_staking_events_info s
        WHERE h.identifier = s.identifier
          AND h.subtype = 'exit'
          AND s.is_exit_or_blocknumber = 1
    """)
    
    # Add Arbitrum One location
    op.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('h', 40)")
    
    # Update EVM transaction tables to use integer primary keys
    # First create new tables with integer tx_id as primary key
    op.execute("""
        CREATE TABLE evm_transactions_new (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            block_number INTEGER NOT NULL,
            from_address TEXT NOT NULL,
            to_address TEXT,
            value TEXT NOT NULL,
            gas TEXT NOT NULL,
            gas_price TEXT NOT NULL,
            gas_used TEXT NOT NULL,
            input_data BLOB NOT NULL,
            nonce INTEGER NOT NULL,
            UNIQUE(tx_hash, chain_id)
        )
    """)
    
    # Copy data to new table
    op.execute("""
        INSERT INTO evm_transactions_new (tx_hash, chain_id, timestamp, block_number, 
                                          from_address, to_address, value, gas, gas_price, 
                                          gas_used, input_data, nonce)
        SELECT tx_hash, chain_id, timestamp, block_number, from_address, to_address, 
               value, gas, gas_price, gas_used, input_data, nonce
        FROM evm_transactions
    """)
    
    # Create new evm_tx_mappings with tx_id reference
    op.execute("""
        CREATE TABLE evm_tx_mappings_new (
            tx_id INTEGER NOT NULL,
            value INTEGER NOT NULL,
            FOREIGN KEY(tx_id) REFERENCES evm_transactions_new(tx_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY (tx_id, value)
        )
    """)
    
    # Migrate evm_tx_mappings data
    op.execute("""
        INSERT INTO evm_tx_mappings_new (tx_id, value)
        SELECT e.tx_id, m.value
        FROM evm_tx_mappings m
        JOIN evm_transactions e ON m.tx_hash = e.tx_hash AND m.chain_id = e.chain_id
        JOIN evm_transactions_new n ON e.tx_hash = n.tx_hash AND e.chain_id = n.chain_id
    """)
    
    # Create new evmtx_address_mappings with tx_id reference
    op.execute("""
        CREATE TABLE evmtx_address_mappings_new (
            address TEXT NOT NULL,
            tx_id INTEGER NOT NULL,
            blockchain INTEGER NOT NULL,
            FOREIGN KEY(tx_id) REFERENCES evm_transactions_new(tx_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY (address, tx_id)
        )
    """)
    
    # Migrate evmtx_address_mappings data
    op.execute("""
        INSERT INTO evmtx_address_mappings_new (address, tx_id, blockchain)
        SELECT a.address, n.tx_id, a.blockchain
        FROM evmtx_address_mappings a
        JOIN evm_transactions e ON a.tx_hash = e.tx_hash AND a.chain_id = e.chain_id
        JOIN evm_transactions_new n ON e.tx_hash = n.tx_hash AND e.chain_id = n.chain_id
    """)
    
    # Create new evm_internal_transactions with tx_id reference
    op.execute("""
        CREATE TABLE evm_internal_transactions_new (
            parent_tx_id INTEGER NOT NULL,
            trace_id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            block_number INTEGER NOT NULL,
            from_address TEXT NOT NULL,
            to_address TEXT,
            value TEXT NOT NULL,
            FOREIGN KEY(parent_tx_id) REFERENCES evm_transactions_new(tx_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(parent_tx_id, trace_id, from_address, to_address, value)
        )
    """)
    
    # Migrate evm_internal_transactions data
    op.execute("""
        INSERT INTO evm_internal_transactions_new 
        SELECT n.tx_id, i.trace_id, i.timestamp, i.block_number, i.from_address, i.to_address, i.value
        FROM evm_internal_transactions i
        JOIN evm_transactions e ON i.parent_tx_hash = e.tx_hash AND i.chain_id = e.chain_id
        JOIN evm_transactions_new n ON e.tx_hash = n.tx_hash AND e.chain_id = n.chain_id
    """)
    
    # Create new evmtx_receipts with tx_id reference
    op.execute("""
        CREATE TABLE evmtx_receipts_new (
            tx_id INTEGER NOT NULL,
            contract_address TEXT,
            status INTEGER NOT NULL,
            type INTEGER NOT NULL,
            FOREIGN KEY(tx_id) REFERENCES evm_transactions_new(tx_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(tx_id)
        )
    """)
    
    # Migrate evmtx_receipts data
    op.execute("""
        INSERT INTO evmtx_receipts_new 
        SELECT n.tx_id, r.contract_address, r.status, r.type
        FROM evmtx_receipts r
        JOIN evm_transactions e ON r.tx_hash = e.tx_hash AND r.chain_id = e.chain_id
        JOIN evm_transactions_new n ON e.tx_hash = n.tx_hash AND e.chain_id = n.chain_id
    """)
    
    # Create new evmtx_receipt_logs with tx_id reference
    op.execute("""
        CREATE TABLE evmtx_receipt_logs_new (
            tx_id INTEGER NOT NULL,
            log_index INTEGER NOT NULL,
            data BLOB NOT NULL,
            address TEXT NOT NULL,
            removed INTEGER NOT NULL,
            FOREIGN KEY(tx_id) REFERENCES evmtx_receipts_new(tx_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(tx_id, log_index)
        )
    """)
    
    # Migrate evmtx_receipt_logs data
    op.execute("""
        INSERT INTO evmtx_receipt_logs_new 
        SELECT n.tx_id, l.log_index, l.data, l.address, l.removed
        FROM evmtx_receipt_logs l
        JOIN evm_transactions e ON l.tx_hash = e.tx_hash AND l.chain_id = e.chain_id
        JOIN evm_transactions_new n ON e.tx_hash = n.tx_hash AND e.chain_id = n.chain_id
    """)
    
    # Create new evmtx_receipt_log_topics with tx_id reference
    op.execute("""
        CREATE TABLE evmtx_receipt_log_topics_new (
            tx_id INTEGER NOT NULL,
            log_index INTEGER NOT NULL,
            topic BLOB NOT NULL,
            topic_index INTEGER NOT NULL,
            FOREIGN KEY(tx_id, log_index) REFERENCES evmtx_receipt_logs_new(tx_id, log_index) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(tx_id, log_index, topic_index)
        )
    """)
    
    # Migrate evmtx_receipt_log_topics data
    op.execute("""
        INSERT INTO evmtx_receipt_log_topics_new 
        SELECT n.tx_id, t.log_index, t.topic, t.topic_index
        FROM evmtx_receipt_log_topics t
        JOIN evm_transactions e ON t.tx_hash = e.tx_hash AND t.chain_id = e.chain_id
        JOIN evm_transactions_new n ON e.tx_hash = n.tx_hash AND e.chain_id = n.chain_id
    """)
    
    # Drop old tables and rename new ones
    op.drop_table('evm_transactions')
    op.drop_table('evm_internal_transactions')
    op.drop_table('evmtx_receipts')
    op.drop_table('evmtx_receipt_logs')
    op.drop_table('evmtx_receipt_log_topics')
    op.drop_table('evm_tx_mappings')
    op.drop_table('evmtx_address_mappings')
    
    op.execute("ALTER TABLE evm_transactions_new RENAME TO evm_transactions")
    op.execute("ALTER TABLE evm_internal_transactions_new RENAME TO evm_internal_transactions")
    op.execute("ALTER TABLE evmtx_receipts_new RENAME TO evmtx_receipts")
    op.execute("ALTER TABLE evmtx_receipt_logs_new RENAME TO evmtx_receipt_logs")
    op.execute("ALTER TABLE evmtx_receipt_log_topics_new RENAME TO evmtx_receipt_log_topics")
    op.execute("ALTER TABLE evm_tx_mappings_new RENAME TO evm_tx_mappings")
    op.execute("ALTER TABLE evmtx_address_mappings_new RENAME TO evmtx_address_mappings")
    
    # Delete polygon etherscan RPC node
    op.execute("DELETE FROM rpc_nodes WHERE name='polygon etherscan'")
    
    # Add binance to current price oracles if not present
    op.execute("""
        UPDATE settings 
        SET value = REPLACE(value, ']', ',"binance"]')
        WHERE name = 'current_price_oracles' 
          AND value NOT LIKE '%binance%'
          AND value LIKE '%]'
    """)
    
    # Reset decoded events except customized ones
    op.execute("""
        DELETE FROM evm_tx_mappings 
        WHERE value = 0 AND tx_id NOT IN (
            SELECT DISTINCT et.tx_id
            FROM history_events he
            JOIN evm_transactions et ON he.event_identifier = et.tx_hash
            JOIN history_events_mappings hem ON he.identifier = hem.parent_identifier
            WHERE hem.name = 'customized' AND hem.value = 1
        )
    """)


def downgrade() -> None:
    """Downgrade from v39 to v38"""
    raise NotImplementedError("Downgrade not implemented for this migration")