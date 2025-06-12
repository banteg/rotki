"""Upgrade from v29 to v30

Revision ID: 029_v29_to_v30
Revises: 028_v28_to_v29
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v29_v30.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '029_v29_to_v30'
down_revision = '028_v28_to_v29'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v29 to v30"""
    # Operations ported from the original upgrade script
    op.execute('\'ALTER TABLE manually_tracked_balances ADD category \'\n            "CHAR(1')
    op.execute('"INSERT OR IGNORE INTO location(location, seq')
    op.execute('ALTER TABLE manually_tracked_balances ADD category \'\n            "CHAR(1) NOT NULL DEFAULT(\'A\') REFERENCES balance_category(category);')



def downgrade() -> None:
    """Downgrade from v30 to v29"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
