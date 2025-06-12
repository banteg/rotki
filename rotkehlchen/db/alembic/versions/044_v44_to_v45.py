"""Upgrade from v44 to v45

Revision ID: 044_v44_to_v45
Revises: 043_v43_to_v44
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v44_v45.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '044_v44_to_v45'
down_revision = '043_v43_to_v44'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v44 to v45"""
    # Operations ported from the original upgrade script
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")



def downgrade() -> None:
    """Downgrade from v45 to v44"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
