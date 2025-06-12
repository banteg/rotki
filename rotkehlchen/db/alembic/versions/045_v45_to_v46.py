"""Upgrade from v45 to v46

Revision ID: 045_v45_to_v46
Revises: 044_v44_to_v45
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v45_v46.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '045_v45_to_v46'
down_revision = '044_v44_to_v45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v45 to v46"""
    # Operations ported from the original upgrade script
    op.execute('"SELECT value FROM settings where name=\'active_modules\'"')
    op.execute('"UPDATE OR IGNORE settings SET value=? WHERE name=\'active_modules\'",\n            (json.dumps([module for module in active_modules if module != \'balancer\']')
    op.add_column('history_events', ...)
    op.execute("'UPDATE history_events SET extra_data = '\n            '(SELECT extra_data FROM evm_events_info '\n            'WHERE evm_events_info.identifier = history_events.identifier")
    op.drop_column('evm_events_info', ...)
    op.execute("'SELECT event_identifier, location_label FROM history_events WHERE event_identifier '\n            'IN (SELECT link FROM asset_movements WHERE location=?")
    op.execute("'DELETE FROM history_events WHERE event_identifier '\n            'IN (SELECT link FROM asset_movements WHERE location=?")
    op.execute("'SELECT id, location, category, address, transaction_id, timestamp, asset, '\n            'amount, fee_asset, fee, link FROM asset_movements',")
    op.drop_table('asset_movements'')
    op.drop_table('asset_movement_category'')
    op.execute('"DELETE FROM settings WHERE name=\'account_for_assets_movements\'"')
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")
    op.execute("(\n                'INSERT OR IGNORE INTO history_events(entry_type, event_identifier, '\n                'sequence_index, timestamp, location, location_label, asset, amount, usd_value, '\n                'notes, type, subtype, extra_data")
    op.add_column('history_events', ...)
    op.drop_column('evm_events_info', ...)
    op.add_column('history_events', ...)
    op.execute("UPDATE history_events SET extra_data = '\n            '(SELECT extra_data FROM evm_events_info '\n            'WHERE evm_events_info.identifier = history_events.identifier);")



def downgrade() -> None:
    """Downgrade from v46 to v45"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
