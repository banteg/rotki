"""Upgrade from v41 to v42

Revision ID: 041_v41_to_v42
Revises: 040_v40_to_v41
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v41_v42.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '041_v41_to_v42'
down_revision = '040_v40_to_v41'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v41 to v42"""
    # Operations ported from the original upgrade script
    op.create_table('zksynclite_tx_type', ...)
    op.execute('"""\n        /* Transfer Type */\n        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq')
    op.execute('"""\n        /* Deposit Type */\n        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq')
    op.execute('"""\n        /* Withdraw Type */\n        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq')
    op.execute('"""\n        /* ChangePubKey Type */\n        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq')
    op.execute('"""\n        /* ForcedExit Type */\n        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq')
    op.execute('"""\n        /* FullExit Type */\n        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq')
    op.execute('"""\n        /* Swap Type */\n        INSERT OR IGNORE INTO zksynclite_tx_type(type, seq')
    op.create_table('zksynclite_transactions', ...)
    op.create_table('zksynclite_swaps', ...)
    op.execute('"SELECT value from settings WHERE name=\'evmchains_to_skip_detection\'"')
    op.execute("'INSERT OR REPLACE INTO settings(name, value")
    op.create_table('calendar', ...)
    op.create_table('calendar_reminders', ...)
    op.execute('"SELECT value FROM settings WHERE name=\'current_price_oracles\'"')
    op.execute("'INSERT OR REPLACE INTO settings(name, value")
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")
    op.drop_table('balancer_events'')
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ?',\n            ('balancer_events%',")
    op.drop_table('yearn_vaults_events'')
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('yearn\\\\_vaults%', '\\\\'")
    op.execute("'DELETE FROM history_events WHERE identifier IN (SELECT identifier FROM evm_events_info '  # noqa: E501\n            'WHERE identifier NOT IN (SELECT eei.identifier FROM evm_events_info eei JOIN '\n            'evm_transactions et ON eei.tx_hash = et.tx_hash")
    op.execute("'INSERT OR IGNORE INTO location(location, seq")
    op.create_table('zksynclite_tx_type', ...)
    op.create_table('zksynclite_transactions', ...)
    op.create_table('zksynclite_swaps', ...)
    op.create_table('calendar', ...)
    op.create_table('calendar_reminders', ...)
    op.execute('UPDATE CASCADE\n        );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n        FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,\n        FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE\n        );')



def downgrade() -> None:
    """Downgrade from v42 to v41"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
