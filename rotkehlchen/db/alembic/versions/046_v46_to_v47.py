"""Upgrade from v46 to v47

Revision ID: 046_v46_to_v47
Revises: 045_v45_to_v46
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v46_v47.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '046_v46_to_v47'
down_revision = '045_v45_to_v46'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v46 to v47"""
    # Operations ported from the original upgrade script
    op.execute("'DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ?',\n            ('extrainternaltx\\\\_%', '\\\\'")
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")
    op.execute("'DELETE FROM history_events WHERE sequence_index > 1 AND event_identifier LIKE ? ESCAPE ?', ('BP1\\\\_%', '\\\\'")
    op.execute('"""\n        UPDATE history_events\n        SET\n            type = \'informational\',\n            subtype = \'mev reward\',\n            notes = \'Validator \' ||\n            (SELECT SE.validator_index FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier')
    op.execute('"""\n        UPDATE history_events\n        SET type = \'informational\'\n        WHERE entry_type = 4 AND sequence_index = 0 AND location_label NOT IN (\n            SELECT account FROM blockchain_accounts WHERE blockchain = \'ETH\'')
    op.execute('\'SELECT identifier FROM assets WHERE identifier IN (\'\n                "SELECT identifier FROM evm_tokens WHERE token_kind = \'B\' "\n                "UNION SELECT REPLACE(identifier, \'erc721\', \'erc20\'')
    op.execute("f'DELETE FROM {table_name} WHERE {column_name} IN ({placeholders}")
    op.execute('"SELECT identifier FROM assets WHERE identifier LIKE \'eip155:%/erc721:0x%\' "\n                "AND identifier NOT LIKE \'eip155:%/erc721:0x%/%\'",')
    op.execute("f'WITH asset_list(value")
    op.create_table('temp_erc721_data', ...)
    op.execute("'INSERT INTO temp_erc721_data(table_name, data")
    op.execute("f'WITH asset_list(value")
    op.execute("'DELETE FROM history_events WHERE location=? AND event_identifier NOT LIKE ?',\n                ((db_loc := location.serialize_for_db(")
    op.execute('"DELETE FROM trades WHERE location=? AND link != \'\'",\n                (db_loc,')
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? OR name LIKE ? OR name LIKE ? OR name LIKE ?',  # noqa: E501\n                (\n                    f'{(loc := location.serialize(")
    op.execute("'DELETE FROM key_value_cache WHERE name LIKE ? OR name LIKE ?',\n            (f'{(coinbase_loc := Location.COINBASE.serialize(")
    op.execute("'SELECT value FROM settings WHERE name=?',\n            ('historical_price_oracles',")
    op.execute("'UPDATE settings SET value=? WHERE name=?',\n            (json.dumps(oracles")
    op.execute("'SELECT value FROM settings WHERE name=?',\n            ('active_modules',")
    op.execute("'UPDATE settings SET value=? WHERE name=?',\n            (json.dumps(modules")
    op.drop_column('history_events', ...)
    op.execute('"DELETE FROM settings WHERE name=\'last_data_upload_ts\'"')
    op.execute('"SELECT m.name as table_name, p.\'from\' as column_name "\n        "FROM sqlite_master m JOIN pragma_foreign_key_list(m.name')
    op.execute("'SELECT COUNT(*")
    op.execute("f'UPDATE {table_name} SET {column_name}=? WHERE {column_name}=?',\n                        (new_id, old_id")
    op.execute("'DELETE FROM assets WHERE identifier = ?', (old_id,")
    op.execute("'UPDATE assets SET identifier=? WHERE identifier=?', (new_id, old_id")
    op.execute('"SELECT value FROM multisettings WHERE name=\'ignored_asset\' AND value "\n            f"IN({\',\'.join([\'?\'] * len(changed_ids_mappings')
    op.execute('"SELECT COUNT(*')
    op.execute('"DELETE FROM multisettings WHERE name=\'ignored_asset\' AND value=?",\n                    (entry[0],')
    op.execute('"UPDATE multisettings SET value=? WHERE name=\'ignored_asset\' AND value=?",\n                    (changed_ids_mappings[entry[0]], entry[0]')
    op.execute("'DELETE FROM accounting_rules WHERE type=? AND subtype=? AND counterparty=?',\n            [\n                (event_type, event_subtype, counterparty")
    op.execute("'DELETE FROM multisettings WHERE name=?',\n            [(f'queried_address_{x}',")
    op.create_table('temp_erc721_data', ...)
    op.drop_column('history_events', ...)
    op.drop_column('history_events', ...)
    op.execute("UPDATE history_events\n        SET\n            type = 'informational',\n            subtype = 'mev reward',\n            notes = 'Validator ' ||\n            (SELECT SE.validator_index FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier) ||\n            ' produced block ' ||\n            (SELECT SE.is_exit_or_blocknumber FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier) ||\n            '. Relayer reported ' ||\n            history_events.amount ||\n            ' ETH as the MEV reward going to ' ||\n            COALESCE(history_events.location_label, 'Unknown')\n        WHERE\n            entry_type = 4 AND\n            sequence_index = 1 AND\n        EXISTS (SELECT 1 FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier);")
    op.execute("UPDATE history_events\n        SET type = 'informational'\n        WHERE entry_type = 4 AND sequence_index = 0 AND location_label NOT IN (\n            SELECT account FROM blockchain_accounts WHERE blockchain = 'ETH'\n        );")
    op.drop_column('history_events', ...)
    op.execute('DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ?\',\n            (\'extrainternaltx\\\\_%\', \'\\\\\'),\n        )\n\n    @progress_step(description=\'Resetting decoded events.\')\n    def _reset_decoded_events(write_cursor: \'DBCursor\') -> None:\n        """Reset all decoded evm events except for the customized ones and those in zksync lite.\n        Code taken from previous upgrade\n        """\n        if write_cursor.execute(\'SELECT COUNT(*) FROM evm_transactions\').fetchone()[0] > 0:\n            customized_events = write_cursor.execute(\n                \'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?\',\n                (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),\n            ).fetchone()[0]\n            querystr = (\n                "DELETE FROM history_events WHERE identifier IN ("\n                "SELECT H.identifier from history_events H INNER JOIN evm_events_info E "\n                "ON H.identifier=E.identifier AND E.tx_hash IN "\n                "(SELECT tx_hash FROM evm_transactions) AND H.location != \'o\')"  # location \'o\' is zksync lite  # noqa: E501\n            )\n            bindings: tuple = ()\n            if customized_events != 0:\n                querystr += \' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)\'  # noqa: E501\n                bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)\n\n            write_cursor.execute(querystr, bindings)\n            write_cursor.execute(\n                \'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?\',  # noqa: E501\n                (0,),  # decoded tx state\n            )\n\n    @progress_step(description=\'Adjust block production events.\')\n    def _adjust_block_production_events(write_cursor: \'DBCursor\') -> None:\n        """Due to the block production changes we need to make sure that all MEV\n        events are recalculated and that we properly use INFORMATIONAL when the recipient\n        is not tracked.\n        """\n        # Delete MEV events that were already moved to the block events. They will rerun\n        write_cursor.execute(\n            \'DELETE FROM history_events WHERE sequence_index > 1 AND event_identifier LIKE ? ESCAPE ?\', (\'BP1\\\\_%\', \'\\\\\'),  # noqa: E501\n        )\n        # Modify all MEV relayer events to be informational and properly display new notes\n        write_cursor.execute("""\n        UPDATE history_events\n        SET\n            type = \'informational\',\n            subtype = \'mev reward\',\n            notes = \'Validator \' ||\n            (SELECT SE.validator_index FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier) ||\n            \' produced block \' ||\n            (SELECT SE.is_exit_or_blocknumber FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier) ||\n            \'. Relayer reported \' ||\n            history_events.amount ||\n            \' ETH as the MEV reward going to \' ||\n            COALESCE(history_events.location_label, \'Unknown\')\n        WHERE\n            entry_type = 4 AND\n            sequence_index = 1 AND\n        EXISTS (SELECT 1 FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier);')
    op.execute("DELETE FROM {table_name} WHERE {column_name} IN ({placeholders})', globaldb_identifiers_to_remove)  # noqa: E501\n\n                global_db_write_cursor.executescript('PRAGMA foreign_keys = ON;")
    op.drop_column('history_events', ...)



def downgrade() -> None:
    """Downgrade from v47 to v46"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
