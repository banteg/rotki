"""Upgrade from v30 to v31

Revision ID: 030_v30_to_v31
Revises: 029_v29_to_v30
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v30_v31.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '030_v30_to_v31'
down_revision = '029_v29_to_v30'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v30 to v31"""
    # Operations ported from the original upgrade script
    op.execute('# always returns value\n        "SELECT count(*')
    op.execute('"DELETE FROM ignored_actions WHERE type=\'C\';"')
    op.create_table('ignored_actions', ...)
    op.execute('"DELETE FROM trades WHERE location=\'B\';"')
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?', ('kraken\\\\_trades\\\\_%', '\\\\'")
    op.drop_table('eth2_deposits')
    op.drop_table('eth2_daily_staking_details')
    op.create_table('eth2_validators', ...)
    op.create_table('eth2_deposits', ...)
    op.create_table('eth2_daily_staking_details', ...)
    op.execute('"""\nCREATE VIEW IF NOT EXISTS combined_trades_view AS\n    WITH amounts_query AS (\n        SELECT\n        A.tx_hash AS txhash,\n        A.log_index AS logindex,\n        A.timestamp AS time,\n        A.location AS location,\n        FE.amount1_in AS first1in,\n        FE.amount0_in AS first0in,\n        FE.token0_identifier AS firsttoken0,\n        FE.token1_identifier AS firsttoken1,\n        LE.amount0_out AS last0out,\n        LE.amount1_out AS last1out,\n        LE.token0_identifier AS lasttoken0,\n        LE.token1_identifier AS lasttoken1\n        FROM amm_swaps A\n        LEFT JOIN amm_swaps FE ON\n        FE.tx_hash = A.tx_hash AND FE.log_index=(SELECT MIN(log_index')
    op.create_table('history_events', ...)
    op.create_table('ignored_actions', ...)
    op.create_table('eth2_validators', ...)
    op.create_table('eth2_deposits', ...)
    op.create_table('eth2_daily_staking_details', ...)
    op.create_table('history_events', ...)
    op.drop_table('eth2_deposits')
    op.drop_table('eth2_daily_staking_details')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n    PRIMARY KEY(tx_hash, pubkey, amount) /* multiple deposits can exist for same pubkey */\n    );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n    PRIMARY KEY (validator_index, timestamp));')
    op.execute("DELETE FROM ignored_actions WHERE type='C';")
    op.execute("DELETE FROM trades WHERE location='B';")
    op.drop_table('eth2_deposits')



def downgrade() -> None:
    """Downgrade from v31 to v30"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
