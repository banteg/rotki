"""v26 to v27

Revision ID: 026_v26_to_v27
Revises: 001_initial_v26
Create Date: 2025-01-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '026_v26_to_v27'
down_revision = '001_initial_v26'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v26 to v27
    
    - Deletes and recreates the tables that were changed after removing UnknownEthereumToken
    """
    # Drop and recreate balancer_events table
    op.drop_table('balancer_events')
    op.execute("""
CREATE TABLE IF NOT EXISTS balancer_events (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_address_token TEXT NOT NULL,
    lp_amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    amount0 TEXT NOT NULL,
    amount1 TEXT NOT NULL,
    amount2 TEXT,
    amount3 TEXT,
    amount4 TEXT,
    amount5 TEXT,
    amount6 TEXT,
    amount7 TEXT,
    FOREIGN KEY (pool_address_token) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
)
    """)
    
    # Drop balancer_pools table
    op.drop_table('balancer_pools')
    
    # Delete balancer query ranges
    op.execute(
        "DELETE FROM used_query_ranges WHERE name LIKE 'balancer\\_events%' ESCAPE '\\'"
    )
    
    # Drop and recreate amm_swaps table
    op.drop_table('amm_swaps')
    op.execute("""
CREATE TABLE IF NOT EXISTS amm_swaps (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    to_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    token0_identifier TEXT NOT NULL,
    token1_identifier TEXT NOT NULL,
    amount0_in TEXT,
    amount1_in TEXT,
    amount0_out TEXT,
    amount1_out TEXT,
    FOREIGN KEY(token0_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
)
    """)
    
    # Delete related query ranges
    op.execute(
        "DELETE FROM used_query_ranges WHERE name LIKE 'balancer\\_trades%' ESCAPE '\\'"
    )
    op.execute(
        "DELETE FROM used_query_ranges WHERE name LIKE 'uniswap\\_trades%' ESCAPE '\\'"
    )
    
    # Drop and recreate uniswap_events table
    op.drop_table('uniswap_events')
    op.execute("""
CREATE TABLE IF NOT EXISTS uniswap_events (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_address VARCHAR[42] NOT NULL,
    token0_identifier TEXT NOT NULL,
    token1_identifier TEXT NOT NULL,
    amount0 TEXT,
    amount1 TEXT,
    usd_price TEXT,
    lp_amount TEXT,
    FOREIGN KEY(token0_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
)
    """)
    
    # Delete uniswap query ranges
    op.execute(
        "DELETE FROM used_query_ranges WHERE name LIKE 'uniswap\\_events%' ESCAPE '\\'"
    )


def downgrade() -> None:
    """Downgrade from v27 to v26"""
    # This would require recreating the old schema with UnknownEthereumToken columns
    raise NotImplementedError("Downgrade not implemented")