"""Initial Alembic migration representing v26 schema

Revision ID: 001_initial_v26
Revises: 
Create Date: 2025-01-06

This migration creates the database schema as of v26.
It serves as the base for transitioning from the old upgrade system to Alembic.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_v26'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables for v26 schema"""
    
    # Create enum tables first
    op.create_table('location',
        sa.Column('location', sa.CHAR(1), primary_key=True, nullable=False),
        sa.Column('seq', sa.INTEGER, unique=True)
    )
    
    # Insert location enum values (simplified for v26)
    locations = [
        ('A', 1), ('B', 2), ('C', 3), ('D', 4), ('E', 5), ('F', 6),
        ('G', 7), ('H', 8), ('I', 9), ('J', 10), ('K', 11), ('L', 12),
        ('M', 13), ('N', 14), ('O', 15), ('P', 16), ('Q', 17), ('R', 18),
        ('S', 19), ('T', 20), ('U', 21), ('V', 22), ('W', 23), ('X', 24),
        ('Y', 25), ('Z', 26), ('[', 27), ('\\\\', 28), (']', 29), ('^', 30),
        ('_', 31), ('`', 32), ('a', 33), ('b', 34), ('c', 35), ('d', 36),
    ]
    
    for loc, seq in locations:
        op.execute(f"INSERT INTO location(location, seq) VALUES ('{loc}', {seq})")
    
    # Create core tables
    op.create_table('assets',
        sa.Column('identifier', sa.TEXT, primary_key=True, nullable=False)
    )
    
    op.create_table('settings',
        sa.Column('name', sa.VARCHAR(24), primary_key=True, nullable=False),
        sa.Column('value', sa.TEXT)
    )
    
    op.create_table('tags',
        sa.Column('name', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('description', sa.TEXT),
        sa.Column('background_color', sa.TEXT),
        sa.Column('foreground_color', sa.TEXT)
    )
    
    # Create blockchain_accounts with label column (as it existed in v26)
    op.create_table('blockchain_accounts',
        sa.Column('blockchain', sa.VARCHAR(24), nullable=False),
        sa.Column('account', sa.TEXT, nullable=False),
        sa.Column('label', sa.TEXT)
    )
    
    op.create_table('ignored_actions',
        sa.Column('identifier', sa.TEXT, primary_key=True)
    )
    
    # Create tables with foreign keys
    op.create_table('tag_mappings',
        sa.Column('object_reference', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('tag_name', sa.TEXT, primary_key=True, nullable=False),
        sa.ForeignKeyConstraint(['tag_name'], ['tags.name'])
    )
    
    op.create_table('timed_balances',
        sa.Column('timestamp', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('currency', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('amount', sa.TEXT),
        sa.Column('usd_value', sa.TEXT),
        sa.ForeignKeyConstraint(['currency'], ['assets.identifier'], onupdate='CASCADE')
    )
    
    op.create_table('timed_location_data',
        sa.Column('timestamp', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('location', sa.CHAR(1), primary_key=True, nullable=False, server_default='A'),
        sa.Column('usd_value', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location'])
    )
    
    op.create_table('user_credentials',
        sa.Column('name', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('location', sa.CHAR(1), primary_key=True, nullable=False, server_default='A'),
        sa.Column('api_key', sa.TEXT),
        sa.Column('api_secret', sa.TEXT),
        sa.Column('passphrase', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location'])
    )
    
    op.create_table('external_service_credentials',
        sa.Column('name', sa.VARCHAR(30), primary_key=True, nullable=False),
        sa.Column('api_key', sa.TEXT, nullable=False),
        sa.Column('api_secret', sa.TEXT)
    )
    
    op.create_table('manually_tracked_balances',
        sa.Column('id', sa.INTEGER, primary_key=True),
        sa.Column('asset', sa.TEXT, nullable=False),
        sa.Column('label', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.ForeignKeyConstraint(['asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['location'], ['location.location'])
    )
    
    op.create_table('ethereum_transactions',
        sa.Column('tx_hash', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('block_number', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.Column('gas', sa.TEXT, nullable=False),
        sa.Column('gas_price', sa.TEXT, nullable=False),
        sa.Column('gas_used', sa.TEXT, nullable=False),
        sa.Column('input_data', sa.TEXT, nullable=False),
        sa.Column('nonce', sa.INTEGER, nullable=False)
    )
    
    op.create_table('ethereum_internal_transactions',
        sa.Column('parent_tx_hash', sa.TEXT, nullable=False),
        sa.Column('trace_id', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('block_number', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['parent_tx_hash'], ['ethereum_transactions.tx_hash'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('parent_tx_hash', 'trace_id')
    )
    
    op.create_table('ethtx_address_mappings',
        sa.Column('address', sa.TEXT, nullable=False),
        sa.Column('tx_hash', sa.TEXT, nullable=False),
        sa.Column('blockchain', sa.TEXT, server_default='ETH'),
        sa.ForeignKeyConstraint(['tx_hash'], ['ethereum_transactions.tx_hash'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('address', 'tx_hash')
    )
    
    op.create_table('xpubs',
        sa.Column('xpub', sa.TEXT, nullable=False),
        sa.Column('derivation_path', sa.TEXT, nullable=False),
        sa.Column('label', sa.TEXT),
        sa.Column('blockchain', sa.TEXT, server_default='BTC'),
        sa.PrimaryKeyConstraint('xpub', 'derivation_path')
    )
    
    op.create_table('xpub_mappings',
        sa.Column('address', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('xpub', sa.TEXT, nullable=False),
        sa.Column('derivation_path', sa.TEXT, nullable=False),
        sa.Column('account_index', sa.INTEGER),
        sa.Column('derived_index', sa.INTEGER)
    )
    
    op.create_table('margin_positions',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('open_time', sa.INTEGER),
        sa.Column('close_time', sa.INTEGER),
        sa.Column('profit_loss', sa.TEXT),
        sa.Column('pl_currency', sa.TEXT, nullable=False),
        sa.Column('fee', sa.TEXT),
        sa.Column('fee_currency', sa.TEXT),
        sa.Column('link', sa.TEXT),
        sa.Column('notes', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location']),
        sa.ForeignKeyConstraint(['pl_currency'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['fee_currency'], ['assets.identifier'], onupdate='CASCADE')
    )
    
    op.create_table('used_query_ranges',
        sa.Column('name', sa.VARCHAR(24), primary_key=True, nullable=False),
        sa.Column('start_ts', sa.INTEGER),
        sa.Column('end_ts', sa.INTEGER)
    )
    
    op.create_table('eth2_validators',
        sa.Column('validator_index', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('public_key', sa.TEXT, nullable=False, unique=True),
        sa.Column('ownership_proportion', sa.TEXT, nullable=False, server_default='1')
    )
    
    op.create_table('eth2_deposits',
        sa.Column('tx_hash', sa.TEXT, nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('pubkey', sa.TEXT, nullable=False),
        sa.Column('withdrawal_credentials', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT, nullable=False),
        sa.Column('usd_value', sa.TEXT, nullable=False),
        sa.Column('validator_index', sa.INTEGER),
        sa.ForeignKeyConstraint(['validator_index'], ['eth2_validators.validator_index']),
        sa.PrimaryKeyConstraint('tx_hash', 'log_index')
    )
    
    op.create_table('eth2_daily_staking_details',
        sa.Column('validator_index', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('start_amount', sa.TEXT, nullable=False),
        sa.Column('end_amount', sa.TEXT, nullable=False),
        sa.Column('pnl', sa.TEXT, nullable=False),
        sa.Column('start_usd_value', sa.TEXT, nullable=False),
        sa.Column('end_usd_value', sa.TEXT, nullable=False),
        sa.Column('pnl_usd_value', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['validator_index'], ['eth2_validators.validator_index'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('validator_index', 'timestamp')
    )
    
    op.create_table('multisettings',
        sa.Column('name', sa.VARCHAR(24), nullable=False),
        sa.Column('value', sa.TEXT),
        sa.UniqueConstraint('name', 'value')
    )
    
    # DeFi tables
    op.create_table('balancer_events',
        sa.Column('tx_hash', sa.VARCHAR(42), nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('address', sa.VARCHAR(42), nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('type', sa.TEXT, nullable=False),
        sa.Column('pool_address_token', sa.TEXT, nullable=False),
        sa.Column('lp_amount', sa.TEXT, nullable=False),
        sa.Column('usd_value', sa.TEXT, nullable=False),
        sa.Column('amount0', sa.TEXT, nullable=False),
        sa.Column('amount1', sa.TEXT, nullable=False),
        sa.Column('amount2', sa.TEXT),
        sa.Column('amount3', sa.TEXT),
        sa.Column('amount4', sa.TEXT),
        sa.Column('amount5', sa.TEXT),
        sa.Column('amount6', sa.TEXT),
        sa.Column('amount7', sa.TEXT),
        sa.ForeignKeyConstraint(['pool_address_token'], ['assets.identifier'], onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'log_index')
    )
    
    op.create_table('uniswap_events',
        sa.Column('tx_hash', sa.VARCHAR(42), nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('address', sa.VARCHAR(42), nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('type', sa.TEXT, nullable=False),
        sa.Column('pool_address', sa.VARCHAR(42), nullable=False),
        sa.Column('token0_identifier', sa.TEXT, nullable=False),
        sa.Column('token1_identifier', sa.TEXT, nullable=False),
        sa.Column('amount0', sa.TEXT),
        sa.Column('amount1', sa.TEXT),
        sa.Column('usd_price', sa.TEXT),
        sa.Column('lp_amount', sa.TEXT),
        sa.ForeignKeyConstraint(['token0_identifier'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['token1_identifier'], ['assets.identifier'], onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'log_index')
    )
    
    op.create_table('amm_swaps',
        sa.Column('tx_hash', sa.VARCHAR(42), nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('address', sa.VARCHAR(42), nullable=False),
        sa.Column('from_address', sa.VARCHAR(42), nullable=False),
        sa.Column('to_address', sa.VARCHAR(42), nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('token0_identifier', sa.TEXT, nullable=False),
        sa.Column('token1_identifier', sa.TEXT, nullable=False),
        sa.Column('amount0_in', sa.TEXT),
        sa.Column('amount1_in', sa.TEXT),
        sa.Column('amount0_out', sa.TEXT),
        sa.Column('amount1_out', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location']),
        sa.ForeignKeyConstraint(['token0_identifier'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['token1_identifier'], ['assets.identifier'], onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'log_index')
    )
    
    # Create trades table
    op.create_table('trades',
        sa.Column('id', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('time', sa.INTEGER, nullable=False),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('base_asset', sa.TEXT, nullable=False),
        sa.Column('quote_asset', sa.TEXT, nullable=False),
        sa.Column('type', sa.CHAR(1), nullable=False),
        sa.Column('amount', sa.TEXT, nullable=False),
        sa.Column('rate', sa.TEXT, nullable=False),
        sa.Column('fee', sa.TEXT),
        sa.Column('fee_currency', sa.TEXT),
        sa.Column('link', sa.TEXT),
        sa.Column('notes', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location']),
        sa.ForeignKeyConstraint(['base_asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['quote_asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['fee_currency'], ['assets.identifier'], onupdate='CASCADE')
    )


def downgrade() -> None:
    """Drop all tables"""
    tables_to_drop = [
        'trades', 'amm_swaps', 'uniswap_events', 'balancer_events',
        'eth2_daily_staking_details', 'eth2_deposits', 'eth2_validators',
        'multisettings', 'used_query_ranges', 'margin_positions',
        'xpub_mappings', 'xpubs', 'ethtx_address_mappings',
        'ethereum_internal_transactions', 'ethereum_transactions',
        'manually_tracked_balances', 'external_service_credentials',
        'user_credentials', 'timed_location_data', 'timed_balances',
        'tag_mappings', 'ignored_actions', 'blockchain_accounts',
        'tags', 'settings', 'assets', 'location'
    ]
    
    for table in tables_to_drop:
        op.drop_table(table)