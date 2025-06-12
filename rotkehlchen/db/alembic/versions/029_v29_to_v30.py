"""Upgrade from v29 to v30

Revision ID: 029_v29_to_v30
Revises: 028_v28_to_v29
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v29_v30.py
"""
from alembic import op
import sqlalchemy as sa
# No longer needed since we're using op.execute

# revision identifiers, used by Alembic.
revision = '029_v29_to_v30'
down_revision = '028_v28_to_v29'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v29 to v30"""
    # Add balance_category table if not exists
    op.create_table('balance_category',
        sa.Column('category', sa.CHAR(1), primary_key=True, nullable=False),
        sa.Column('seq', sa.INTEGER, unique=True)
    )
    
    # Insert balance category values
    op.execute("INSERT OR IGNORE INTO balance_category(category, seq) VALUES ('A', 1)")  # Asset
    op.execute("INSERT OR IGNORE INTO balance_category(category, seq) VALUES ('B', 2)")  # Liability
    
    # We need to disable foreign_keys to add the column due to the constraint:
    # Cannot add a REFERENCES column with non-NULL default value
    op.execute('PRAGMA foreign_keys=OFF')
    op.execute(
        'ALTER TABLE manually_tracked_balances ADD category '
        "CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category)"
    )
    op.execute('PRAGMA foreign_keys=ON')
    
    # Insert the new bitpanda location
    op.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('b', 34)")



def downgrade() -> None:
    """Downgrade from v30 to v29"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
