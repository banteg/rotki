"""Upgrade from v39 to v40

Revision ID: 039_v39_to_v40
Revises: 038_v38_to_v39
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v39_v40.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '039_v39_to_v40'
down_revision = '038_v38_to_v39'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v39 to v40"""
    # Operations ported from the original upgrade script
    op.create_table('skipped_external_events', ...)
    op.create_table('accounting_rules', ...)
    op.create_table('linked_rules_properties', ...)
    op.create_table('unresolved_remote_conflicts', ...)
    op.execute("'DELETE from used_query_ranges WHERE name=?', ('last_withdrawals_query_ts',")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',\n            (f'{Location.KRAKEN!s}\\\\_%', '\\\\'")
    op.execute("f'DELETE FROM {table} WHERE location = ?;', (location,")
    op.execute("'SELECT value FROM settings WHERE name=?', ('taxable_ledger_actions',")
    op.execute("'INSERT INTO accounting_rules(type, subtype, counterparty, taxable, '\n            'count_entire_amount_spend, count_cost_basis_pnl, '\n            'accounting_treatment")
    op.execute("'SELECT timestamp, type, location, amount, asset, rate, rate_asset, link, notes FROM ledger_actions'")
    op.drop_table('ledger_actions')
    op.drop_table('ledger_action_type')
    op.execute("'DELETE from settings WHERE name=?', ('taxable_ledger_actions',")
    op.execute("'SELECT name FROM used_query_ranges WHERE name LIKE ? ESCAPE ?', ('%\\\\_ledger\\\\_actions\\\\_%', '\\\\'")
    op.execute("'UPDATE used_query_ranges SET name = ? WHERE name = ?',\n                        (entry[0].replace('_ledger_actions_', '_history_events_'")
    op.execute("'DELETE FROM ignored_actions WHERE type=?', ('D',")
    op.execute("'DELETE FROM action_type WHERE type=?', ('D',")
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions")
    op.execute("'DELETE from assets WHERE identifier=?;',\n            (target_asset_identifier,")
    op.execute("'UPDATE assets SET identifier=? WHERE identifier=?;',\n            (target_asset_identifier, source_identifier")
    op.execute("# update types by event identifier\n            'UPDATE history_events SET type=?, subtype=? WHERE '\n            'event_identifier LIKE ? AND type=? AND subtype=?',\n            [(\n                to_type.serialize(")
    op.execute("# update types for all the locations\n            'UPDATE history_events SET type=?, subtype=? WHERE type=? AND subtype=?',\n            [(\n                to_type.serialize(")
    op.execute("'INSERT OR IGNORE INTO location(location, seq")
    op.execute('"""INSERT OR IGNORE INTO history_events(\n        entry_type,\n        event_identifier,\n        sequence_index,\n        timestamp,\n        location,\n        location_label,\n        asset,\n        amount,\n        usd_value,\n        notes,\n        type,\n        subtype')
    op.create_table('skipped_external_events', ...)
    op.create_table('accounting_rules', ...)
    op.create_table('linked_rules_properties', ...)
    op.create_table('unresolved_remote_conflicts', ...)
    op.drop_table('ledger_actions')
    op.drop_table('ledger_action_type')
    op.drop_table('ledger_actions')
    op.execute('UPDATE history_events SET type=?, subtype=? WHERE \'\n            \'event_identifier LIKE ? AND type=? AND subtype=?\',\n            [(\n                to_type.serialize(), to_subtype.serialize(), PREFIX,\n                from_type.serialize(), from_subtype.serialize(),\n            ) for to_type, to_subtype, from_type, from_subtype in CHANGES],\n        )\n        write_cursor.executemany(  # update types for all the locations\n            \'UPDATE history_events SET type=?, subtype=? WHERE type=? AND subtype=?\',\n            [(\n                to_type.serialize(), to_subtype.serialize(),\n                from_type.serialize(), from_subtype.serialize(),\n            ) for to_type, to_subtype, from_type, from_subtype in TYPES_REMAPPED],\n        )\n        write_cursor.execute(\'DELETE from used_query_ranges WHERE name=?\', (\'last_withdrawals_query_ts\',))  # noqa: E501\n\n    @progress_step(description=\'Purging Kraken events.\')\n    def _purge_kraken_events(write_cursor: \'DBCursor\') -> None:\n        """\n        Purge kraken events, after the changes that allows for processing of new assets.\n        We may have had missed events so now let\'s repull. And since we will also\n        get https://github.com/rotki/rotki/issues/6582 this resetting should not need to\n        happen in the future.\n\n        This just mimics DBHandler::purge_exchange_data\n        """\n        write_cursor.execute(\n            \'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;')
    op.execute('UPDATE CASCADE,\n            UNIQUE(event_identifier, sequence_index)""",\n        )\n        write_cursor.executescript(\'PRAGMA foreign_keys = ON;')
    op.execute('UPDATE used_query_ranges SET name = ? WHERE name = ?\',\n                        (entry[0].replace(\'_ledger_actions_\', \'_history_events_\'), entry[0]),\n                    )\n                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member\n                    log.error(f\'Failed to update used query range {entry[0]} due to {e}\')\n                    continue\n\n        # Clean up any ignored ledger actions # THINK: Migrate the ignoring if action exists and is migrated to history event or let user do it again? Probably let\'s keep it simple  # noqa: E501\n        write_cursor.execute(\'DELETE FROM ignored_actions WHERE type=?\', (\'D\',))\n        write_cursor.execute(\'DELETE FROM action_type WHERE type=?\', (\'D\',))\n\n    @progress_step(description=\'Resetting decoded events.\')\n    def _reset_decoded_events(write_cursor: \'DBCursor\') -> None:\n        """\n        Reset all decoded evm events except the customized ones for ethereum mainnet,\n        arbitrum, optimism and polygon.\n        """\n        if write_cursor.execute(\'SELECT COUNT(*) FROM evm_transactions\').fetchone()[0] == 0:\n            return\n\n        customized_events = write_cursor.execute(\n            \'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?\',\n            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),\n        ).fetchone()[0]\n        querystr = (\n            \'DELETE FROM history_events WHERE identifier IN (\'\n            \'SELECT H.identifier from history_events H INNER JOIN evm_events_info E \'\n            \'ON H.identifier=E.identifier AND E.tx_hash IN \'\n            \'(SELECT tx_hash FROM evm_transactions))\'\n        )\n        bindings: tuple = ()\n        if customized_events != 0:\n            querystr += \' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)\'  # noqa: E501\n            bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)\n\n        write_cursor.execute(querystr, bindings)\n        write_cursor.execute(\n            \'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?\',  # noqa: E501\n            (0,),  # decoded state\n        )\n\n    @progress_step(description=\'Replacing velo identifier.\')\n    def _replace_velo_identifier(write_cursor: \'DBCursor\') -> None:\n        """\n        Replace VELO with the binance version of the token. This is done as part of a consolidation\n        process where we added VELO V1 and VELO V2 from Velodrome but our database also contained a\n        VELO asset and a BNB version of it both not related to velodrome. As part of upgrade to V6\n        of the global DB we are replacing this VELO asset (not token) with its BNB version.\n\n        Code taken from replace_asset_identifier\n        """\n        target_asset_identifier = \'eip155:56/erc20:0xf486ad071f3bEE968384D2E39e2D8aF0fCf6fd46\'\n        source_identifier = \'VELO\'\n\n        write_cursor.executescript(\'PRAGMA foreign_keys = OFF;')
    op.execute('UPDATE assets SET identifier=? WHERE identifier=?;')
    op.execute('DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;')
    op.execute('DELETE FROM {table} WHERE location = ?;')
    op.execute('DELETE FROM ignored_actions WHERE type=?\', (\'D\',))\n        write_cursor.execute(\'DELETE FROM action_type WHERE type=?\', (\'D\',))\n\n    @progress_step(description=\'Resetting decoded events.\')\n    def _reset_decoded_events(write_cursor: \'DBCursor\') -> None:\n        """\n        Reset all decoded evm events except the customized ones for ethereum mainnet,\n        arbitrum, optimism and polygon.\n        """\n        if write_cursor.execute(\'SELECT COUNT(*) FROM evm_transactions\').fetchone()[0] == 0:\n            return\n\n        customized_events = write_cursor.execute(\n            \'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?\',\n            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),\n        ).fetchone()[0]\n        querystr = (\n            \'DELETE FROM history_events WHERE identifier IN (\'\n            \'SELECT H.identifier from history_events H INNER JOIN evm_events_info E \'\n            \'ON H.identifier=E.identifier AND E.tx_hash IN \'\n            \'(SELECT tx_hash FROM evm_transactions))\'\n        )\n        bindings: tuple = ()\n        if customized_events != 0:\n            querystr += \' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)\'  # noqa: E501\n            bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)\n\n        write_cursor.execute(querystr, bindings)\n        write_cursor.execute(\n            \'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?\',  # noqa: E501\n            (0,),  # decoded state\n        )\n\n    @progress_step(description=\'Replacing velo identifier.\')\n    def _replace_velo_identifier(write_cursor: \'DBCursor\') -> None:\n        """\n        Replace VELO with the binance version of the token. This is done as part of a consolidation\n        process where we added VELO V1 and VELO V2 from Velodrome but our database also contained a\n        VELO asset and a BNB version of it both not related to velodrome. As part of upgrade to V6\n        of the global DB we are replacing this VELO asset (not token) with its BNB version.\n\n        Code taken from replace_asset_identifier\n        """\n        target_asset_identifier = \'eip155:56/erc20:0xf486ad071f3bEE968384D2E39e2D8aF0fCf6fd46\'\n        source_identifier = \'VELO\'\n\n        write_cursor.executescript(\'PRAGMA foreign_keys = OFF;')



def downgrade() -> None:
    """Downgrade from v40 to v39"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
