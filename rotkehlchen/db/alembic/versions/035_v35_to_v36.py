"""Upgrade from v35 to v36

Revision ID: 035_v35_to_v36
Revises: 034_v34_to_v35
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v35_v36.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '035_v35_to_v36'
down_revision = '034_v34_to_v35'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v35 to v36"""
    # Operations ported from the original upgrade script
    op.drop_table('adex_events'')
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n                ('adex\\\\_events%', '\\\\'")
    op.execute('"SELECT value FROM settings where name=\'active_modules\'"')
    op.execute('"UPDATE OR IGNORE settings SET value=? WHERE name=\'active_modules\'",\n                (json.dumps(new_value')
    op.execute('"UPDATE ignored_actions SET identifier = \'1\' || identifier WHERE type=\'C\'"')
    op.execute("'SELECT * FROM accounts_details'")
    op.drop_table('accounts_details')
    op.create_table('evm_accounts_details', ...)
    op.execute("'SELECT * from ethereum_transactions'")
    op.execute("'SELECT * from ethereum_internal_transactions'")
    op.execute("'SELECT * from ethtx_receipts'")
    op.execute("'SELECT * from ethtx_receipt_logs'")
    op.execute("'SELECT * from ethtx_receipt_log_topics'")
    op.execute("'SELECT * from ethtx_address_mappings'")
    op.execute("'SELECT * from evm_tx_mappings'")
    op.drop_table('ethereum_transactions'')
    op.drop_table('ethereum_internal_transactions'')
    op.drop_table('ethtx_receipts'')
    op.drop_table('ethtx_receipt_logs'')
    op.drop_table('ethtx_receipt_log_topics'')
    op.drop_table('ethtx_address_mappings'')
    op.drop_table('evm_tx_mappings'')
    op.create_table('evm_transactions', ...)
    op.create_table('evm_internal_transactions', ...)
    op.create_table('evmtx_receipts', ...)
    op.create_table('evmtx_receipt_logs', ...)
    op.create_table('evmtx_receipt_log_topics', ...)
    op.create_table('evmtx_address_mappings', ...)
    op.create_table('evm_tx_mappings', ...)
    op.execute("'SELECT * FROM history_events_mappings'")
    op.drop_table('history_events_mappings'')
    op.create_table('history_events_mappings', ...)
    op.drop_table('nfts'')
    op.create_table('nfts', ...)
    op.execute('"SELECT name, endpoint, owned, active, weight, \'ETH\' from web3_nodes",')
    op.drop_table('web3_nodes'')
    op.create_table('rpc_nodes', ...)
    op.execute("'SELECT A.blockchain, A.account, B.tag_name from blockchain_accounts AS A '\n            'LEFT OUTER JOIN tag_mappings AS B on A.account = B.object_reference',")
    op.execute('"INSERT OR IGNORE INTO location(location, seq')
    op.drop_table('eth_tokens'')
    op.execute("'SELECT validator_index, pnl FROM eth2_daily_staking_details WHERE timestamp=?',\n            (1606780800,")
    op.execute("'SELECT tx_hash from evm_transactions'")
    op.execute("'SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?',\n            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED")
    op.execute('"""INSERT OR IGNORE INTO evm_accounts_details(\n            account, chain_id, key, value')
    op.execute('"""\n            INSERT OR IGNORE INTO evm_transactions(\n                tx_hash,\n                chain_id,\n                timestamp,\n                block_number,\n                from_address,\n                to_address,\n                value,\n                gas,\n                gas_price,\n                gas_used,\n                input_data,\n                nonce')
    op.execute('"""\n            INSERT OR IGNORE INTO evm_internal_transactions(\n                parent_tx_hash,\n                chain_id,\n                trace_id,\n                timestamp,\n                block_number,\n                from_address,\n                to_address,\n                value')
    op.execute('"""\n            INSERT OR IGNORE INTO evmtx_receipts(\n                tx_hash,\n                chain_id,\n                contract_address,\n                status,\n                type')
    op.execute('"""\n            INSERT OR IGNORE INTO evmtx_receipt_logs(\n                tx_hash,\n                chain_id,\n                log_index,\n                data,\n                address,\n                removed')
    op.execute('"""\n            INSERT OR IGNORE INTO evmtx_receipt_log_topics(\n                tx_hash,\n                chain_id,\n                log_index,\n                topic,\n                topic_index')
    op.execute('"""\n            INSERT OR IGNORE INTO evmtx_address_mappings(\n                address,\n                tx_hash,\n                chain_id,\n                blockchain')
    op.execute('"""\n            INSERT OR IGNORE INTO evm_tx_mappings(\n                tx_hash,\n                chain_id,\n                value')
    op.execute('"""\n            INSERT OR IGNORE INTO history_events_mappings(\n                parent_identifier,\n                name,\n                value')
    op.execute("'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain")
    op.execute("'DELETE from tag_mappings WHERE object_reference=?', delete_tuples")
    op.execute("'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name")
    op.execute("'UPDATE eth2_daily_staking_details SET pnl=? WHERE validator_index=? AND timestamp=?',  # noqa: E501\n                fixed_values,")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',\n            [(tx_hash, ChainID.ETHEREUM.serialize_for_db(")
    op.create_table('evm_accounts_details', ...)
    op.create_table('evm_transactions', ...)
    op.create_table('evm_internal_transactions', ...)
    op.create_table('evmtx_receipts', ...)
    op.create_table('evmtx_receipt_logs', ...)
    op.create_table('evmtx_receipt_log_topics', ...)
    op.create_table('evmtx_address_mappings', ...)
    op.create_table('evm_tx_mappings', ...)
    op.create_table('history_events_mappings', ...)
    op.create_table('nfts', ...)
    op.create_table('rpc_nodes', ...)
    op.drop_table('adex_events')')
    op.create_table('evm_transactions', ...)
    op.create_table('history_events_mappings', ...)
    op.create_table('nfts', ...)
    op.create_table('rpc_nodes', ...)
    op.drop_table('accounts_details')
    op.execute('UPDATE CASCADE,\n                PRIMARY KEY(parent_tx_hash, chain_id, trace_id, from_address, to_address, value)\n            );')
    op.execute('UPDATE CASCADE,\n                PRIMARY KEY(tx_hash, chain_id)\n            );')
    op.execute('UPDATE CASCADE,\n                PRIMARY KEY(tx_hash, chain_id, log_index)\n            );')
    op.execute('UPDATE CASCADE,\n                PRIMARY KEY(tx_hash, chain_id, log_index, topic_index)\n            );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n                PRIMARY KEY (address, tx_hash, chain_id)\n            );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n                PRIMARY KEY (tx_hash, chain_id, value)\n            );')
    op.execute('UPDATE CASCADE ON DELETE CASCADE,\n                PRIMARY KEY (parent_identifier, name, value)\n            );')
    op.execute('UPDATE CASCADE,\n                FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE\n            );')
    op.drop_table('accounts_details')



def downgrade() -> None:
    """Downgrade from v36 to v35"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
