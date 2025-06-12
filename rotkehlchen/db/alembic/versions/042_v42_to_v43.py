"""Upgrade from v42 to v43

Revision ID: 042_v42_to_v43
Revises: 041_v41_to_v42
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v42_v43.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '042_v42_to_v43'
down_revision = '041_v41_to_v42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v42 to v43"""
    # Operations ported from the original upgrade script
    op.add_column('nfts', ...)
    op.execute("'UPDATE evm_events_info SET counterparty=? WHERE counterparty=?',\n            ('hop', 'hop-protocol'")
    op.execute("'INSERT OR IGNORE INTO location(location, seq")
    op.execute("'DELETE FROM user_credentials WHERE location=?;',\n            (Location.COINBASEPRO.serialize_for_db(")
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")
    op.add_column('nfts', ...)
    op.execute("UPDATE evm_events_info SET counterparty=? WHERE counterparty=?',\n            ('hop', 'hop-protocol'),\n        )\n\n    @progress_step(description='Adding new supported locations.')\n    def _add_new_supported_locations(write_cursor: 'DBCursor') -> None:\n        write_cursor.execute(\n            'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',\n            ('p', Location.HTX.value),\n        )\n\n    @progress_step(description='Removing Coinbase Pro credentials.')\n    def _remove_coinbasepro_credentials(write_cursor: 'DBCursor') -> None:\n        write_cursor.execute(\n            'DELETE FROM user_credentials WHERE location=?;")
    op.execute('DELETE FROM user_credentials WHERE location=?;')



def downgrade() -> None:
    """Downgrade from v43 to v42"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
