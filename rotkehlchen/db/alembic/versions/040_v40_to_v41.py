"""Upgrade from v40 to v41

Revision ID: 040_v40_to_v41
Revises: 039_v39_to_v40
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v40_v41.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '040_v40_to_v41'
down_revision = '039_v39_to_v40'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v40 to v41"""
    # Operations ported from the original upgrade script
    op.execute("'SELECT name, end_ts FROM used_query_ranges WHERE name LIKE ?',\n        (pattern,")
    op.create_table('key_value_cache', ...)
    op.execute("'DELETE FROM external_service_credentials WHERE name=?',\n            ('covalent',")
    op.execute("'DELETE FROM user_credentials WHERE location=?',\n            (Location.BITTREX.serialize_for_db(")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',\n            (f'{Location.BITTREX!s}\\\\_%', '\\\\'")
    op.execute('"SELECT value FROM settings WHERE name=\'non_syncing_exchanges\'",')
    op.execute('"UPDATE settings SET value=? WHERE name=\'non_syncing_exchanges\'",\n                    (json.dumps(new_values')
    op.execute('f\'SELECT name, value FROM settings WHERE name IN ({",".join(["?"] * len(settings_moved')
    op.execute('f\'DELETE FROM settings WHERE name IN ({",".join(["?"] * len(movable_settings')
    op.execute("'INSERT OR IGNORE INTO location(location, seq")
    op.execute('# get priority settings\n            "SELECT value FROM settings WHERE name = \'address_name_priority\'",')
    op.execute("'SELECT account, blockchain, label FROM blockchain_accounts WHERE label IS NOT NULL',  # noqa: E501")
    op.execute("'SELECT address, blockchain FROM address_book;',")
    op.drop_column('blockchain_accounts', ...)
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")
    op.execute("'DELETE FROM history_events WHERE location=? AND type=? AND subtype=?',\n            ('B', 'informational', 'fee'")
    op.execute("'INSERT OR IGNORE INTO key_value_cache(name, value")
    op.execute("'DELETE FROM used_query_ranges WHERE name = ?', [(row[0],")
    op.execute("'INSERT OR IGNORE INTO key_value_cache(name, value")
    op.execute("# insert all the prioritized labels into the address_book table\n            'INSERT OR REPLACE INTO address_book(address, blockchain, name")
    op.create_table('key_value_cache', ...)
    op.drop_column('blockchain_accounts', ...)
    op.execute('UPDATE settings SET value=? WHERE name=\'non_syncing_exchanges\'",\n                    (json.dumps(new_values),),\n                )\n\n    @progress_step(description=\'Upgrading external service credentials.\')\n    def _upgrade_external_service_credentials(write_cursor: \'DBCursor\') -> None:\n        """Upgrade the external service credentials schema table to add a secret"""\n        update_table_schema(\n            write_cursor=write_cursor,\n            table_name=\'external_service_credentials\',\n            schema="""name VARCHAR[30] NOT NULL PRIMARY KEY,\n            api_key TEXT NOT NULL,\n            api_secret TEXT""",\n            insert_columns=\'name,api_key,null\',\n        )\n\n    @progress_step(description=\'Moving non settings mappings to cache.\')\n    def _move_non_settings_mappings_to_cache(write_cursor: \'DBCursor\') -> None:\n        """Move the non-settings value from `settings` to a separate `key_value_cache` table"""\n        settings_moved = (\n            \'last_balance_save\',\n            \'last_data_upload_ts\',\n            \'last_data_updates_ts\',\n            \'last_owned_assets_update\',\n            \'last_evm_accounts_detect_ts\',\n            \'last_spam_assets_detect_key\',\n            \'last_augmented_spam_assets_detect_key\',\n        )\n        movable_settings = write_cursor.execute(\n            f\'SELECT name, value FROM settings WHERE name IN ({",".join(["?"] * len(settings_moved))});')
    op.create_table('key_value_cache', ...)
    op.execute('DELETE FROM external_service_credentials WHERE name=?\',\n            (\'covalent\', ),\n        )\n\n    @progress_step(description=\'Removing Bittrex data.\')\n    def _remove_bittrex_data(write_cursor: \'DBCursor\') -> None:\n        """\n        Removes bittrex settings and credentials from the DB.\n        Code taken from v36->v37 upgrade from ftx.\n        """\n        write_cursor.execute(\n            \'DELETE FROM user_credentials WHERE location=?\',\n            (Location.BITTREX.serialize_for_db(),),\n        )\n        write_cursor.execute(\n            \'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;')
    op.execute('DELETE FROM settings WHERE name IN ({",".join(["?"] * len(movable_settings))});')
    op.execute('DELETE FROM history_events WHERE identifier IN (\'\n                \'SELECT H.identifier from history_events H INNER JOIN evm_events_info E \'\n                \'ON H.identifier=E.identifier AND E.tx_hash IN \'\n                \'(SELECT tx_hash FROM evm_transactions))\'\n            )\n            bindings: tuple = ()\n            if customized_events != 0:\n                querystr += \' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)\'  # noqa: E501\n                bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)\n\n            write_cursor.execute(querystr, bindings)\n            write_cursor.execute(\n                \'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?\',  # noqa: E501\n                (0,),  # 0 -> decoded tx state\n            )\n\n    @progress_step(description=\'Upgrading eth2 validators.\')\n    def _upgrade_eth2_validators(write_cursor: \'DBCursor\') -> None:\n        """\n        Upgrade the eth2 validators DB table while preserving eth2 daily stats table.\n        Foreign keys off so that recreation of table does not delete all daily stats"""\n        write_cursor.executescript(\'PRAGMA foreign_keys = OFF;')



def downgrade() -> None:
    """Downgrade from v41 to v40"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
