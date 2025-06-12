"""Upgrade from v27 to v28

Revision ID: 027_v27_to_v28
Revises: 026_v26_to_v27
Create Date: 2025-01-06

This upgrade includes:
- Add version column to yearn vaults events
- Delete aave information due to the addition of aave 2
- Add Gitcoin tables
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '027_v27_to_v28'
down_revision = '026_v26_to_v27'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v27 to v28"""
    
    # Add version column to yearn_vaults_events if it doesn't exist
    # Check if table exists first
    op.execute("""
        CREATE TABLE IF NOT EXISTS yearn_vaults_events (
            tx_hash VARCHAR[42] NOT NULL,
            log_index INTEGER NOT NULL,
            from_address VARCHAR[42] NOT NULL,
            to_address VARCHAR[42] NOT NULL,
            timestamp INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            from_asset TEXT NOT NULL,
            from_amount TEXT NOT NULL,
            from_usd_value TEXT NOT NULL,
            to_asset TEXT NOT NULL,
            to_amount TEXT NOT NULL,
            to_usd_value TEXT NOT NULL,
            pnl_amount TEXT,
            pnl_usd_value TEXT,
            block_number INTEGER NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY (to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (tx_hash, log_index, from_address, to_address)
        )
    """)
    
    # Try to add version column if it doesn't exist
    try:
        op.add_column('yearn_vaults_events',
            sa.Column('version', sa.INTEGER, nullable=False, server_default='1')
        )
    except:
        pass  # Column might already exist
    
    # Delete aave data if table exists
    op.execute('DROP TABLE IF EXISTS aave_events')
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'aave\\_events%' ESCAPE '\\'")
    
    # Create aave_events table if needed for this version
    op.execute("""CREATE TABLE IF NOT EXISTS aave_events (
        address VARCHAR[42] NOT NULL,
        event_type VARCHAR[10] NOT NULL,
        timestamp INTEGER NOT NULL,
        asset TEXT NOT NULL,
        amount TEXT NOT NULL,
        usd_value TEXT NOT NULL,
        block_number INTEGER NOT NULL,
        tx_hash VARCHAR[66] NOT NULL,
        log_index INTEGER NOT NULL,
        FOREIGN KEY (asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
        PRIMARY KEY (address, event_type, timestamp, tx_hash, log_index)
    )""")
    
    # Create Gitcoin tables
    op.create_table('gitcoin_tx_type',
        sa.Column('type', sa.CHAR(1), primary_key=True, nullable=False),
        sa.Column('seq', sa.INTEGER, nullable=True, unique=True)
    )
    
    # Insert Gitcoin transaction types
    op.execute("INSERT OR IGNORE INTO gitcoin_tx_type(type, seq) VALUES ('A', 1)")  # Ethereum Transaction
    op.execute("INSERT OR IGNORE INTO gitcoin_tx_type(type, seq) VALUES ('B', 2)")  # ZKSync Transaction
    
    op.create_table('ledger_actions_gitcoin_data',
        sa.Column('parent_id', sa.INTEGER, nullable=False),
        sa.Column('tx_id', sa.TEXT, nullable=False, unique=True),
        sa.Column('grant_id', sa.INTEGER, nullable=False),
        sa.Column('clr_round', sa.INTEGER),
        sa.Column('tx_type', sa.CHAR(1), nullable=False, server_default='A'),
        sa.ForeignKeyConstraint(['tx_type'], ['gitcoin_tx_type.type']),
        sa.ForeignKeyConstraint(['parent_id'], ['ledger_actions.identifier'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('parent_id')
    )
    
    op.create_table('gitcoin_grant_metadata',
        sa.Column('grant_id', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('grant_name', sa.TEXT, nullable=False),
        sa.Column('created_on', sa.INTEGER, nullable=False)
    )


def downgrade() -> None:
    """Downgrade from v28 to v27"""
    raise NotImplementedError("Downgrade not implemented for this migration")