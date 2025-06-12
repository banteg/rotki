"""Upgrade from v31 to v32

Revision ID: 031_v31_to_v32
Revises: 030_v30_to_v31
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v31_v32.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '031_v31_to_v32'
down_revision = '030_v30_to_v31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v31 to v32"""
    # Operations ported from the original upgrade script
    op.execute('"""\n        DELETE FROM history_events where location=\'B\' AND asset=\'KFEE\' AND\n         type=\'trade\' AND subtype=NULL;\n        """')
    op.execute("'SELECT event_identifier, sequence_index from history_events'")
    op.execute('"""\n        SELECT e.event_identifier, e.sequence_index, e.identifier from history_events e JOIN (SELECT event_identifier,\n        sequence_index, COUNT(*')
    op.create_table('history_events_copy', ...)
    op.execute("'UPDATE history_events SET timestamp = timestamp / 10;'")
    op.execute('"UPDATE history_events SET subtype = \'deposit asset\' WHERE subtype = \'staking deposit asset\';"')
    op.execute('"UPDATE history_events SET subtype = \'receive wrapped\' WHERE subtype = \'staking receive asset\';"')
    op.execute('"UPDATE history_events SET subtype = \'remove asset\', type = \'staking\' WHERE subtype = \'staking remove asset\' AND type = \'unstaking\';"')
    op.execute('"UPDATE history_events SET subtype = \'return wrapped\', type = \'staking\' WHERE subtype = \'staking receive asset\' AND type = \'unstaking\';"')
    op.execute('"UPDATE history_events SET type = \'informational\' WHERE subtype = \'unknown\';"')
    op.execute('"""\n        INSERT INTO history_events_copy (event_identifier, sequence_index, timestamp, location,\n        location_label, asset, amount, usd_value, notes, type, subtype')
    op.drop_table('history_events')
    op.execute("'ALTER TABLE history_events_copy RENAME TO history_events;'")
    op.execute('"UPDATE history_events SET subtype=\'reward\' WHERE type=\'staking\' AND subtype IS NULL;",')
    op.execute("'DELETE from ledger_actions WHERE identifier IN (SELECT parent_id FROM ledger_actions_gitcoin_data")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('gitcoingrants\\\\_%', '\\\\'")
    op.drop_table('gitcoin_grant_metadata'')
    op.drop_table('ledger_actions_gitcoin_data'')
    op.drop_table('gitcoin_tx_type'')
    op.execute('"INSERT OR IGNORE INTO location(location, seq')
    op.create_table('ethereum_internal_transactions', ...)
    op.create_table('ethtx_address_mappings', ...)
    op.create_table('evm_tx_mappings', ...)
    op.create_table('history_events_mappings', ...)
    op.create_table('ens_mappings', ...)
    op.execute("'UPDATE trades SET fee = NULL WHERE fee_currency IS NULL'")
    op.execute("'UPDATE trades SET fee_currency = NULL WHERE fee IS NULL'")
    op.execute('"""\n        UPDATE user_credentials_mappings SET setting_name = ? WHERE setting_name = \'PAIRS\'\n        """, (BINANCE_MARKETS_KEY,')
    op.execute("'SELECT id, label FROM manually_tracked_balances'")
    op.execute("'UPDATE tag_mappings SET object_reference=? WHERE object_reference=?', (balance_id, label")
    op.execute("'UPDATE history_events SET sequence_index=? WHERE identifier=?',\n                update_tuples,")
    op.create_table('history_events_copy', ...)
    op.create_table('ethereum_internal_transactions', ...)
    op.create_table('ethtx_address_mappings', ...)
    op.create_table('evm_tx_mappings', ...)
    op.create_table('history_events_mappings', ...)
    op.create_table('ens_mappings', ...)
    op.execute('ALTER TABLE history_events_copy RENAME TO history_events;')
    op.drop_table('history_events')
    op.create_table('ethereum_internal_transactions', ...)
    op.execute('INSERT INTO history_events_copy (event_identifier, sequence_index, timestamp, location,\n        location_label, asset, amount, usd_value, notes, type, subtype)\n        SELECT event_identifier, sequence_index, timestamp, location, location_label, asset,\n        amount, usd_value, notes, type, subtype\n        FROM history_events;')
    op.create_table('history_events_copy', ...)
    op.execute('UPDATE history_events SET timestamp = timestamp / 10;')
    op.execute("UPDATE history_events SET subtype = 'deposit asset' WHERE subtype = 'staking deposit asset';")
    op.execute("UPDATE history_events SET subtype = 'receive wrapped' WHERE subtype = 'staking receive asset';")
    op.execute("UPDATE history_events SET subtype = 'remove asset', type = 'staking' WHERE subtype = 'staking remove asset' AND type = 'unstaking';")
    op.execute("UPDATE history_events SET subtype = 'return wrapped', type = 'staking' WHERE subtype = 'staking receive asset' AND type = 'unstaking';")
    op.execute("UPDATE history_events SET type = 'informational' WHERE subtype = 'unknown';")
    op.execute("UPDATE history_events SET subtype='reward' WHERE type='staking' AND subtype IS NULL;")
    op.execute('UPDATE CASCADE,\n        PRIMARY KEY(parent_tx_hash, trace_id)\n    );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n        PRIMARY KEY (address, tx_hash, blockchain)\n    );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n        PRIMARY KEY (tx_hash, value)\n    );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n        PRIMARY KEY (parent_identifier, value)\n    );')
    op.execute("DELETE FROM history_events where location='B' AND asset='KFEE' AND\n         type='trade' AND subtype=NULL;")
    op.create_table('ethereum_internal_transactions', ...)



def downgrade() -> None:
    """Downgrade from v32 to v31"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
