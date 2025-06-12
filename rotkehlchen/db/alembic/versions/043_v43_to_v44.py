"""Upgrade from v43 to v44

Revision ID: 043_v43_to_v44
Revises: 042_v42_to_v43
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v43_v44.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '043_v43_to_v44'
down_revision = '042_v42_to_v43'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v43 to v44"""
    # Operations ported from the original upgrade script
    op.create_table('nfts_new', ...)
    op.execute("'SELECT identifier, name, last_price, last_price_asset, manual_price, owner_address, '\n            'is_lp, image_url, collection_name, usd_price FROM nfts',")
    op.drop_table('nfts'')
    op.execute("'ALTER TABLE nfts_new RENAME TO nfts'")
    op.drop_column('evmtx_receipt_logs', ...)
    op.execute("'SELECT object_reference, tag_name FROM tag_mappings',")
    op.execute("'SELECT value FROM settings WHERE name=?', ('historical_price_oracles',")
    op.execute("'INSERT OR REPLACE INTO settings(name, value")
    op.add_column('eth2_validators', ...)
    op.create_table('cowswap_orders', ...)
    op.create_table('gnosispay_data', ...)
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('zksynclitetxs\\\\_%', '\\\\'")
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")
    op.execute("'UPDATE assets SET identifier=? WHERE identifier=?',\n            assets_updates,")
    op.execute("'INSERT OR IGNORE INTO nfts_new(identifier, name, last_price, last_price_asset, '\n            'manual_price, owner_address, is_lp, image_url, collection_name, usd_price")
    op.execute("'DELETE FROM tag_mappings WHERE object_reference=?', remove_keys")
    op.execute("'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name")
    op.create_table('nfts_new', ...)
    op.create_table('cowswap_orders', ...)
    op.create_table('gnosispay_data', ...)
    op.execute('ALTER TABLE nfts_new RENAME TO nfts\')\n\n    @progress_step(description=\'Removing log column "removed".\')\n    def _remove_log_removed_column(write_cursor: \'DBCursor\') -> None:\n        write_cursor.execute(\n            \'ALTER TABLE evmtx_receipt_logs DROP COLUMN removed;')
    op.create_table('cowswap_orders', ...)
    op.execute('DROP TABLE nfts\')\n        write_cursor.execute(\'ALTER TABLE nfts_new RENAME TO nfts\')\n\n    @progress_step(description=\'Removing log column "removed".\')\n    def _remove_log_removed_column(write_cursor: \'DBCursor\') -> None:\n        write_cursor.execute(\n            \'ALTER TABLE evmtx_receipt_logs DROP COLUMN removed;')
    op.execute('UPDATE CASCADE,\n            FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE\n        );')
    op.execute('UPDATE assets SET identifier=? WHERE identifier=?\',\n            assets_updates,\n        )\n        write_cursor.executemany(\n            \'INSERT OR IGNORE INTO nfts_new(identifier, name, last_price, last_price_asset, \'\n            \'manual_price, owner_address, is_lp, image_url, collection_name, usd_price) \'\n            \'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\',\n            final_rows,\n        )\n        write_cursor.execute(\'DROP TABLE nfts\')\n        write_cursor.execute(\'ALTER TABLE nfts_new RENAME TO nfts\')\n\n    @progress_step(description=\'Removing log column "removed".\')\n    def _remove_log_removed_column(write_cursor: \'DBCursor\') -> None:\n        write_cursor.execute(\n            \'ALTER TABLE evmtx_receipt_logs DROP COLUMN removed;')
    op.create_table('cowswap_orders', ...)



def downgrade() -> None:
    """Downgrade from v44 to v43"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
