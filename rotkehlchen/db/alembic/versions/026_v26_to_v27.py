"""Upgrade from v26 to v27

Revision ID: 026_v26_to_v27
Revises: 001_initial_v48
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v26_v27.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '026_v26_to_v27'
down_revision = '001_initial_v48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v26 to v27"""
    # Operations ported from the original upgrade script
    op.drop_table('balancer_events')
    op.create_table('balancer_events', ...)
    op.drop_table('balancer_pools')
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n        ('balancer\\\\_events%', '\\\\'")
    op.drop_table('amm_swaps')
    op.create_table('amm_swaps', ...)
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n        ('balancer\\\\_trades%', '\\\\'")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n        ('uniswap\\\\_trades%', '\\\\'")
    op.drop_table('uniswap_events')
    op.create_table('uniswap_events', ...)
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n        ('uniswap\\\\_events%', '\\\\'")
    op.create_table('balancer_events', ...)
    op.create_table('amm_swaps', ...)
    op.create_table('uniswap_events', ...)
    op.drop_table('balancer_events')
    op.drop_table('balancer_pools')
    op.drop_table('amm_swaps')
    op.drop_table('uniswap_events')
    op.execute('UPDATE CASCADE,\n    PRIMARY KEY (tx_hash, log_index)\n);')
    op.execute('UPDATE CASCADE,\n    FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,\n    PRIMARY KEY (tx_hash, log_index)\n);')
    op.execute('UPDATE CASCADE,\n    FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,\n    PRIMARY KEY (tx_hash, log_index)\n);')
    op.drop_table('amm_swaps')
    op.drop_table('uniswap_events')



def downgrade() -> None:
    """Downgrade from v27 to v26"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
