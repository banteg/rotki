"""Upgrade from v38 to v39

Revision ID: 038_v38_to_v39
Revises: 037_v37_to_v38
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v38_v39.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '038_v38_to_v39'
down_revision = '037_v37_to_v38'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v38 to v39"""
    # Operations ported from the original upgrade script
    op.create_table('optimism_transactions', ...)
    op.execute("'SELECT H.identifier, H.subtype, S.validator_index, S.is_exit_or_blocknumber, '\n            'H.timestamp FROM history_events H INNER JOIN eth_staking_events_info S '\n            'ON S.identifier=H.identifier',")
    op.execute("'SELECT identifier, event_identifier FROM history_events WHERE '\n            'event_identifier LIKE ? ESCAPE ?', ('rotki\\\\_events\\\\_%', '\\\\'")
    op.execute("'SELECT * from evm_transactions'")
    op.execute("'SELECT * from evm_internal_transactions'")
    op.execute("'SELECT * from evmtx_receipts'")
    op.execute("'SELECT * from evmtx_receipt_logs'")
    op.execute("'SELECT * from evmtx_receipt_log_topics'")
    op.execute("'SELECT * from evm_tx_mappings'")
    op.execute("'SELECT tx_hash, chain_id, address from evmtx_address_mappings'")
    op.drop_table('evm_transactions'')
    op.drop_table('evm_internal_transactions'')
    op.drop_table('evmtx_receipts'')
    op.drop_table('evmtx_receipt_logs'')
    op.drop_table('evmtx_receipt_log_topics'')
    op.drop_table('evm_tx_mappings'')
    op.drop_table('evmtx_address_mappings'')
    op.create_table('evm_transactions', ...)
    op.create_table('evm_tx_mappings', ...)
    op.create_table('evmtx_address_mappings', ...)
    op.create_table('evm_internal_transactions', ...)
    op.create_table('evmtx_receipts', ...)
    op.create_table('evmtx_receipt_logs', ...)
    op.create_table('evmtx_receipt_log_topics', ...)
    op.execute('"INSERT OR IGNORE INTO location(location, seq')
    op.execute('"SELECT COUNT(*')
    op.execute('"DELETE FROM rpc_nodes WHERE name=\'polygon etherscan\'"')
    op.execute('"SELECT value FROM settings WHERE name=\'current_price_oracles\'"')
    op.execute("'INSERT OR REPLACE INTO settings(name, value")
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")
    op.execute("'UPDATE history_events SET event_identifier=? WHERE identifier=?', updates,")
    op.execute("'INSERT INTO evm_transactions(identifier, tx_hash, chain_id, timestamp, block_number, '\n            'from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce")
    op.execute("'INSERT INTO evm_tx_mappings(tx_id, value")
    op.execute("'INSERT INTO evmtx_address_mappings(tx_id, address")
    op.execute("'INSERT INTO evm_internal_transactions(parent_tx, trace_id, from_address, to_address, '\n            'value")
    op.execute("'INSERT INTO evmtx_receipts(tx_id, contract_address, status, type")
    op.execute("'INSERT INTO evmtx_receipt_logs(identifier, tx_id, log_index, data, address, '\n            'removed")
    op.execute("'INSERT INTO evmtx_receipt_log_topics(log, topic, topic_index")
    op.create_table('optimism_transactions', ...)
    op.create_table('evm_transactions', ...)
    op.create_table('evm_tx_mappings', ...)
    op.create_table('evmtx_address_mappings', ...)
    op.create_table('evm_internal_transactions', ...)
    op.create_table('evmtx_receipts', ...)
    op.create_table('evmtx_receipt_logs', ...)
    op.create_table('evmtx_receipt_log_topics', ...)
    op.create_table('evm_transactions', ...)
    op.create_table('evm_tx_mappings', ...)
    op.create_table('evmtx_address_mappings', ...)
    op.create_table('evm_internal_transactions', ...)
    op.create_table('evmtx_receipts', ...)
    op.create_table('evmtx_receipt_logs', ...)
    op.create_table('evmtx_receipt_log_topics', ...)
    op.execute('INSERT INTO evmtx_receipt_log_topics(log, topic, topic_index) \'\n            \'VALUES(?, ?, ?)\',\n            [(hashchainlog_to_id[x[0] + x[1].to_bytes(4, byteorder=\'big\') + x[2].to_bytes(4, byteorder=\'big\')], *x[3:]) for x in topics],  # noqa: E501\n        )\n\n    @progress_step(description=\'Adding Arbitrum One location\')\n    def _add_arbitrum_one_location(write_cursor: \'DBCursor\') -> None:\n        write_cursor.execute("INSERT OR IGNORE INTO location(location, seq) VALUES (\'i\', 41);')
    op.create_table('optimism_transactions', ...)
    op.create_table('evm_transactions', ...)
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n            PRIMARY KEY (tx_id, value)\n        );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n            PRIMARY KEY (tx_id, address)\n        );')
    op.execute('UPDATE CASCADE,\n            PRIMARY KEY(parent_tx, trace_id, from_address, to_address, value)\n        );')
    op.execute('UPDATE CASCADE\n        );')
    op.execute('UPDATE CASCADE,\n            UNIQUE(tx_id, log_index)\n        );')
    op.execute('UPDATE CASCADE,\n            PRIMARY KEY(log, topic_index)\n        );')



def downgrade() -> None:
    """Downgrade from v39 to v38"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
