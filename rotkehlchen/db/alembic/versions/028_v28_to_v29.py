"""Upgrade from v28 to v29

Revision ID: 028_v28_to_v29
Revises: 027_v27_to_v28
Create Date: 2025-01-06

This upgrade includes:
- Create ethereum transaction receipt tables
- Create NFTs table
- Update blockchain_accounts to use composite primary key
- Update xpub_mappings structure
- Rename uniswap_events to amm_events
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '028_v28_to_v29'
down_revision = '027_v27_to_v28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v28 to v29"""
    
    # First update blockchain_accounts to use composite primary key
    # Save existing data
    op.execute("""
        CREATE TEMPORARY TABLE blockchain_accounts_backup AS
        SELECT blockchain, account, label FROM blockchain_accounts
    """)
    
    # Drop and recreate with new structure
    op.drop_table('blockchain_accounts')
    op.create_table('blockchain_accounts',
        sa.Column('blockchain', sa.VARCHAR(3), nullable=False),
        sa.Column('account', sa.TEXT, nullable=False),
        sa.Column('label', sa.TEXT),
        sa.PrimaryKeyConstraint('blockchain', 'account')
    )
    
    # Restore data
    op.execute("""
        INSERT INTO blockchain_accounts(blockchain, account, label)
        SELECT blockchain, account, label FROM blockchain_accounts_backup
    """)
    op.execute("DROP TABLE blockchain_accounts_backup")
    
    # Update xpub_mappings structure
    op.execute("""
        CREATE TEMPORARY TABLE xpub_mappings_backup AS
        SELECT address, xpub, derivation_path, account_index, derived_index 
        FROM xpub_mappings
    """)
    
    op.drop_table('xpub_mappings')
    op.create_table('xpub_mappings',
        sa.Column('xpub', sa.TEXT, nullable=False),
        sa.Column('derivation_path', sa.TEXT, nullable=False),
        sa.Column('account_index', sa.INTEGER, nullable=False),
        sa.Column('derived_index', sa.INTEGER, nullable=False),
        sa.Column('address', sa.TEXT, nullable=False),
        sa.PrimaryKeyConstraint('address')
    )
    
    op.execute("""
        INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index)
        SELECT address, xpub, derivation_path, account_index, derived_index 
        FROM xpub_mappings_backup
    """)
    op.execute("DROP TABLE xpub_mappings_backup")
    
    # Update ethereum_transactions to use BLOB for tx_hash
    op.execute("""
        CREATE TEMPORARY TABLE ethereum_transactions_backup AS
        SELECT tx_hash, timestamp, block_number, from_address, to_address, 
               value, gas, gas_price, gas_used, input_data, nonce 
        FROM ethereum_transactions
    """)
    
    op.drop_table('ethereum_transactions')
    op.create_table('ethereum_transactions',
        sa.Column('tx_hash', sa.BLOB, primary_key=True, nullable=False),
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
    
    op.execute("""
        INSERT INTO ethereum_transactions
        SELECT CAST(tx_hash AS BLOB), timestamp, block_number, from_address, to_address, 
               value, gas, gas_price, gas_used, CAST(input_data AS BLOB), nonce 
        FROM ethereum_transactions_backup
    """)
    op.execute("DROP TABLE ethereum_transactions_backup")
    
    # Create receipt tables
    op.create_table('ethtx_receipts',
        sa.Column('tx_hash', sa.BLOB, primary_key=True, nullable=False),
        sa.Column('contract_address', sa.TEXT),
        sa.Column('status', sa.INTEGER, nullable=False),
        sa.Column('type', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash'], ['ethereum_transactions.tx_hash'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.CheckConstraint('status IN (0, 1)')
    )
    
    op.create_table('ethtx_receipt_logs',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('data', sa.BLOB, nullable=False),
        sa.Column('address', sa.TEXT, nullable=False),
        sa.Column('removed', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash'], ['ethtx_receipts.tx_hash'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'log_index'),
        sa.CheckConstraint('removed IN (0, 1)')
    )
    
    op.create_table('ethtx_receipt_log_topics',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('topic', sa.BLOB, nullable=False),
        sa.Column('topic_index', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_hash', 'log_index'], ['ethtx_receipt_logs.tx_hash', 'ethtx_receipt_logs.log_index'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'log_index', 'topic_index')
    )
    
    # Create NFTs table
    op.create_table('nfts',
        sa.Column('identifier', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('name', sa.TEXT),
        sa.Column('last_price', sa.TEXT),
        sa.Column('last_price_asset', sa.TEXT),
        sa.Column('manual_price', sa.INTEGER, nullable=False),
        sa.Column('owner_address', sa.TEXT),
        sa.Column('blockchain', sa.TEXT, server_default='ETH'),
        sa.ForeignKeyConstraint(['blockchain', 'owner_address'], ['blockchain_accounts.blockchain', 'blockchain_accounts.account'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['identifier'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['last_price_asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.CheckConstraint('manual_price IN (0, 1)')
    )
    
    # Rename uniswap_events to amm_events
    op.execute('DROP TABLE IF EXISTS amm_events')
    op.execute('ALTER TABLE uniswap_events RENAME TO amm_events')


def downgrade() -> None:
    """Downgrade from v29 to v28"""
    raise NotImplementedError("Downgrade not implemented for this migration")