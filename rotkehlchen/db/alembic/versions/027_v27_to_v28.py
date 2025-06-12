"""Upgrade from v27 to v28

Revision ID: 027_v27_to_v28
Revises: 026_v26_to_v27
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v27_v28.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '027_v27_to_v28'
down_revision = '026_v26_to_v27'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v27 to v28"""
    # Operations ported from the original upgrade script
    op.execute('"SELECT COUNT(*')
    op.add_column('yearn_vaults_events', ...)
    op.execute("'DELETE FROM aave_events;'")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('aave\\\\_events%', '\\\\'")
    op.create_table('gitcoin_tx_type', ...)
    op.execute('"INSERT OR IGNORE INTO gitcoin_tx_type(type, seq')
    op.execute('"INSERT OR IGNORE INTO gitcoin_tx_type(type, seq')
    op.create_table('ledger_actions_gitcoin_data', ...)
    op.create_table('gitcoin_grant_metadata', ...)
    op.add_column('yearn_vaults_events', ...)
    op.execute('DELETE FROM aave_events;')



def downgrade() -> None:
    """Downgrade from v28 to v27"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
