"""Upgrade from v28 to v29

Revision ID: 028_v28_to_v29
Revises: 027_v27_to_v28
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v28_v29.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '028_v28_to_v29'
down_revision = '027_v27_to_v28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v28 to v29"""
    # Operations ported from the original upgrade script
    op.create_table('ethtx_receipts', ...)
    op.create_table('ethtx_receipt_logs', ...)
    op.create_table('ethtx_receipt_log_topics', ...)
    op.create_table('nfts', ...)
    op.execute("'SELECT blockchain, account, label FROM blockchain_accounts;'")
    op.execute("'SELECT address, xpub, derivation_path, account_index, derived_index FROM xpub_mappings;'")
    op.execute("'SELECT tx_hash, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce FROM ethereum_transactions;'")
    op.drop_table('blockchain_accounts')
    op.drop_table('xpub_mappings')
    op.drop_table('ethereum_transactions')
    op.create_table('blockchain_accounts', ...)
    op.create_table('xpub_mappings', ...)
    op.create_table('ethereum_transactions', ...)
    op.drop_table('amm_events')
    op.execute("'ALTER TABLE uniswap_events RENAME TO amm_events;'")
    op.execute("'INSERT INTO blockchain_accounts(blockchain, account, label")
    op.execute("'INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index")
    op.execute("'INSERT INTO ethereum_transactions(tx_hash, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce")
    op.create_table('ethtx_receipts', ...)
    op.create_table('ethtx_receipt_logs', ...)
    op.create_table('ethtx_receipt_log_topics', ...)
    op.create_table('nfts', ...)
    op.create_table('blockchain_accounts', ...)
    op.create_table('xpub_mappings', ...)
    op.create_table('ethereum_transactions', ...)
    op.execute('ALTER TABLE uniswap_events RENAME TO amm_events;')
    op.drop_table('blockchain_accounts')
    op.drop_table('xpub_mappings')
    op.drop_table('ethereum_transactions')
    op.drop_table('amm_events')
    op.execute('INSERT INTO blockchain_accounts(blockchain, account, label) VALUES(?, ?, ?);')
    op.execute("INSERT INTO xpub_mappings(address, xpub, derivation_path, account_index, derived_index) '\n        'VALUES(?, ?, ?, ?, ?);")
    op.execute("INSERT INTO ethereum_transactions(tx_hash, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce) '  # noqa: E501\n        'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);")
    op.execute('UPDATE CASCADE\n    );')
    op.execute('UPDATE CASCADE,\n    PRIMARY KEY(tx_hash, log_index)\n    );')
    op.execute('UPDATE CASCADE,\n    PRIMARY KEY(tx_hash, log_index, topic_index)\n    );')
    op.execute('UPDATE CASCADE,\n    FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE\n    );')



def downgrade() -> None:
    """Downgrade from v29 to v28"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
