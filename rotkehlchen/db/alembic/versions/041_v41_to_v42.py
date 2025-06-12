"""Upgrade from v41 to v42

Revision ID: 041_v41_to_v42
Revises: 040_v40_to_v41
Create Date: 2025-01-06

This upgrade includes:
- Create new tables for zksync lite
- Add new supported locations
- Add a new table to handle the calendar
- Remove the manualcurrent oracle from settings
- Remove balancer old events
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '041_v41_to_v42'
down_revision = '040_v40_to_v41'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v41 to v42"""
    
    # Create zksynclite_tx_type table
    op.create_table('zksynclite_tx_type',
        sa.Column('type', sa.CHAR(1), primary_key=True, nullable=False),
        sa.Column('seq', sa.INTEGER, nullable=False, autoincrement=True)
    )
    
    # Insert zksynclite transaction types
    op.execute("""
        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES
        ('A', 1),  /* Transfer Type */
        ('B', 2),  /* Deposit Type */
        ('C', 3),  /* Withdraw Type */
        ('D', 4),  /* ChangePubKey Type */
        ('E', 5),  /* ForcedExit Type */
        ('F', 6),  /* FullExit Type */
        ('G', 7)   /* Swap Type */
    """)
    
    # Create zksynclite_transactions table
    op.create_table('zksynclite_transactions',
        sa.Column('identifier', sa.INTEGER, primary_key=True, autoincrement=True, nullable=False),
        sa.Column('tx_hash', sa.TEXT, nullable=False),
        sa.Column('type', sa.CHAR(1), nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('block_number', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('asset', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT, nullable=False),
        sa.Column('fee', sa.TEXT),
        sa.ForeignKeyConstraint(['type'], ['zksynclite_tx_type.type']),
        sa.ForeignKeyConstraint(['asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.UniqueConstraint('tx_hash')
    )
    
    # Create zksynclite_swaps table
    op.create_table('zksynclite_swaps',
        sa.Column('tx_id', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('from_asset', sa.TEXT, nullable=False),
        sa.Column('from_amount', sa.TEXT, nullable=False),
        sa.Column('to_asset', sa.TEXT, nullable=False),
        sa.Column('to_amount', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['tx_id'], ['zksynclite_transactions.identifier'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['to_asset'], ['assets.identifier'], onupdate='CASCADE')
    )
    
    # Add zksynclite to evmchains_to_skip_detection if not present
    op.execute("""
        UPDATE settings 
        SET value = json_set(
            COALESCE(value, '[]'), 
            '$[' || json_array_length(COALESCE(value, '[]')) || ']', 
            10
        )
        WHERE name = 'evmchains_to_skip_detection' 
          AND NOT EXISTS (
            SELECT 1 FROM json_each(value) WHERE value = 10
          )
    """)
    
    # If setting doesn't exist, create it
    op.execute("""
        INSERT OR IGNORE INTO settings(name, value) 
        VALUES ('evmchains_to_skip_detection', '[10]')
    """)
    
    # Create calendar table
    op.create_table('calendar',
        sa.Column('identifier', sa.INTEGER, primary_key=True, autoincrement=True, nullable=False),
        sa.Column('name', sa.TEXT, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('description', sa.TEXT),
        sa.Column('color', sa.TEXT, nullable=False, server_default='E8F1EB'),
        sa.Column('auto_delete', sa.INTEGER, nullable=False, server_default='0')
    )
    
    # Create calendar_reminders table
    op.create_table('calendar_reminders',
        sa.Column('identifier', sa.INTEGER, primary_key=True, autoincrement=True, nullable=False),
        sa.Column('event_id', sa.INTEGER, nullable=False),
        sa.Column('secs_before', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['calendar.identifier'], ondelete='CASCADE')
    )
    
    # Remove manualcurrent from current_price_oracles
    op.execute("""
        UPDATE settings 
        SET value = REPLACE(REPLACE(value, ',"manualcurrent"', ''), '"manualcurrent",', '')
        WHERE name = 'current_price_oracles' AND value LIKE '%manualcurrent%'
    """)
    
    # Delete balancer events and related data
    op.drop_table('balancer_events')
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'balancer_events%'")
    
    # Delete yearn vault events and related data
    op.drop_table('yearn_vaults_events')
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'yearn\\_vaults%' ESCAPE '\\'")
    
    # Clean up orphaned evm_events_info
    op.execute("""
        DELETE FROM history_events 
        WHERE identifier IN (
            SELECT identifier FROM evm_events_info 
            WHERE identifier NOT IN (
                SELECT eei.identifier 
                FROM evm_events_info eei 
                JOIN evm_transactions et ON eei.tx_hash = et.tx_hash
            )
        )
    """)
    
    # Add new locations
    op.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('m', 42)")  # zksynclite
    
    # Reset decoded events except customized ones
    op.execute("""
        DELETE FROM evm_tx_mappings 
        WHERE tx_id IN (
            SELECT tx_id FROM evm_transactions
        ) AND value = 0 AND tx_id NOT IN (
            SELECT DISTINCT et.tx_id
            FROM history_events he
            JOIN evm_transactions et ON he.event_identifier = et.tx_hash
            JOIN history_events_mappings hem ON he.identifier = hem.parent_identifier
            WHERE hem.name = 'customized' AND hem.value = 1
        )
    """)


def downgrade() -> None:
    """Downgrade from v42 to v41"""
    raise NotImplementedError("Downgrade not implemented for this migration")