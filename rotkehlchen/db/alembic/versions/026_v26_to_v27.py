"""Upgrade from v26 to v27

Revision ID: 026_v26_to_v27
Revises: 001_initial_v48
Create Date: 2025-01-06

This upgrade includes:
- Update balancer tables structure
- Update amm_swaps table
- Update uniswap_events table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '026_v26_to_v27'
down_revision = '001_initial_v26'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v26 to v27"""
    
    # Update balancer tables
    op.execute('DROP TABLE IF EXISTS balancer_events')
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
    
    op.execute('DROP TABLE IF EXISTS balancer_pools')
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'balancer\\_events%' ESCAPE '\\'")
    
    # Update amm_swaps table
    op.execute('DROP TABLE IF EXISTS amm_swaps')
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
    
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'balancer\\_trades%' ESCAPE '\\'")
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'uniswap\\_trades%' ESCAPE '\\'")
    
    # Update uniswap_events table
    op.execute('DROP TABLE IF EXISTS uniswap_events')
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
    
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'uniswap\\_events%' ESCAPE '\\'")


def downgrade() -> None:
    """Downgrade from v27 to v26"""
    raise NotImplementedError("Downgrade not implemented for this migration")