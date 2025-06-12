"""Upgrade from v31 to v32

Revision ID: 031_v31_to_v32
Revises: 030_v30_to_v31
Create Date: 2025-01-06

This upgrade includes:
- Fix history events timestamps and subtypes
- Remove gitcoin-related tables
- Add EVM and ENS mapping tables
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '031_v31_to_v32'
down_revision = '030_v30_to_v31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v31 to v32"""
    
    # Clean up Kraken fee entries
    op.execute("""
        DELETE FROM history_events 
        WHERE location='B' AND asset='KFEE' AND type='trade' AND subtype IS NULL
    """)
    
    # Create a copy of history_events table with new structure
    op.create_table('history_events_copy',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('event_identifier', sa.TEXT, nullable=False),
        sa.Column('sequence_index', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('location_label', sa.TEXT),
        sa.Column('asset', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT, nullable=False),
        sa.Column('usd_value', sa.TEXT, nullable=False),
        sa.Column('notes', sa.TEXT),
        sa.Column('type', sa.TEXT, nullable=False),
        sa.Column('subtype', sa.TEXT),
        sa.ForeignKeyConstraint(['asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['location'], ['location.location']),
        sa.UniqueConstraint('event_identifier', 'sequence_index')
    )
    
    # Fix timestamps (were multiplied by 10 in error)
    op.execute("UPDATE history_events SET timestamp = timestamp / 10")
    
    # Update subtypes
    op.execute("UPDATE history_events SET subtype = 'deposit asset' WHERE subtype = 'staking deposit asset'")
    op.execute("UPDATE history_events SET subtype = 'receive wrapped' WHERE subtype = 'staking receive asset'")
    op.execute("UPDATE history_events SET subtype = 'remove asset', type = 'staking' WHERE subtype = 'staking remove asset' AND type = 'unstaking'")
    op.execute("UPDATE history_events SET subtype = 'return wrapped', type = 'staking' WHERE subtype = 'staking receive asset' AND type = 'unstaking'")
    op.execute("UPDATE history_events SET type = 'informational' WHERE subtype = 'unknown'")
    
    # Copy data to new table (excluding duplicates)
    op.execute("""
        INSERT INTO history_events_copy (
            event_identifier, sequence_index, timestamp, location,
            location_label, asset, amount, usd_value, notes, type, subtype
        )
        SELECT DISTINCT 
            event_identifier, sequence_index, timestamp, location,
            location_label, asset, amount, usd_value, notes, type, subtype
        FROM history_events
    """)
    
    # Replace old table with new one
    op.drop_table('history_events')
    op.execute("ALTER TABLE history_events_copy RENAME TO history_events")
    
    # Final subtype update
    op.execute("UPDATE history_events SET subtype='reward' WHERE type='staking' AND subtype IS NULL")
    
    # Remove gitcoin-related data and tables
    op.execute("""
        DELETE FROM ledger_actions 
        WHERE identifier IN (
            SELECT parent_id FROM ledger_actions_gitcoin_data
        )
    """)
    
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'gitcoingrants\\_%' ESCAPE '\\'")
    
    # Drop gitcoin tables
    op.drop_table('gitcoin_grant_metadata')
    op.drop_table('ledger_actions_gitcoin_data')
    op.drop_table('gitcoin_tx_type')
    
    # Add new location for Gitcoin
    op.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('^', 30)")
    
    # Create new tables
    op.create_table('ethereum_internal_transactions',
        sa.Column('parent_tx_hash', sa.BLOB, nullable=False),
        sa.Column('trace_id', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['parent_tx_hash'], ['ethereum_transactions.tx_hash'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('parent_tx_hash', 'trace_id', 'from_address', 'to_address', 'value')
    )
    
    op.create_table('ethtx_address_mappings',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('address', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash'], ['ethereum_transactions.tx_hash'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'address')
    )
    
    op.create_table('evm_tx_mappings',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('blockchain', sa.INTEGER, nullable=False),
        sa.Column('value', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash', 'blockchain'], ['evm_transactions.tx_hash', 'evm_transactions.blockchain'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'blockchain', 'value')
    )
    
    op.create_table('history_events_mappings',
        sa.Column('parent_identifier', sa.INTEGER, nullable=False),
        sa.Column('name', sa.TEXT, nullable=False),
        sa.Column('value', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['parent_identifier'], ['history_events.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('parent_identifier', 'name', 'value')
    )
    
    op.create_table('ens_mappings',
        sa.Column('address', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('ens_name', sa.TEXT),
        sa.Column('last_update', sa.INTEGER)
    )
    
    # Clean up trades table
    op.execute("UPDATE trades SET fee = NULL WHERE fee_currency IS NULL")
    op.execute("UPDATE trades SET fee_currency = NULL WHERE fee IS NULL")
    
    # Update binance credentials mapping
    op.execute("""
        UPDATE user_credentials_mappings 
        SET setting_name = 'binance_markets' 
        WHERE setting_name = 'PAIRS'
    """)


def downgrade() -> None:
    """Downgrade from v32 to v31"""
    raise NotImplementedError("Downgrade not implemented for this migration")