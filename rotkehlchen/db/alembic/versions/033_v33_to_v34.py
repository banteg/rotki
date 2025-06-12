"""Upgrade from v33 to v34

Revision ID: 033_v33_to_v34
Revises: 032_v32_to_v33
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v33_v34.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '033_v33_to_v34'
down_revision = '032_v32_to_v33'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v33 to v34"""
    # Operations ported from the original upgrade script
    op.execute("'DROP VIEW combined_trades_view;'")
    op.execute('"""\n        CREATE VIEW IF NOT EXISTS combined_trades_view AS\n            WITH amounts_query AS (\n                SELECT\n                A.tx_hash AS txhash,\n                A.log_index AS logindex,\n                A.timestamp AS time,\n                A.location AS location,\n                FE.amount1_in AS first1in,\n                FE.amount0_in AS first0in,\n                FE.token0_identifier AS firsttoken0,\n                FE.token1_identifier AS firsttoken1,\n                LE.amount0_out AS last0out,\n                LE.amount1_out AS last1out,\n                LE.token0_identifier AS lasttoken0,\n                LE.token1_identifier AS lasttoken1\n                FROM amm_swaps A\n                LEFT JOIN amm_swaps FE ON\n                FE.tx_hash = A.tx_hash AND FE.log_index=(SELECT MIN(log_index')



def downgrade() -> None:
    """Downgrade from v34 to v33"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
