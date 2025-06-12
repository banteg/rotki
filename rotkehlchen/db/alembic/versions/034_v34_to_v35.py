"""Upgrade from v34 to v35

Revision ID: 034_v34_to_v35
Revises: 033_v33_to_v34
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v34_v35.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '034_v34_to_v35'
down_revision = '033_v33_to_v34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v34 to v35"""
    # Operations ported from the original upgrade script
    op.execute("'SELECT value FROM settings WHERE name=?', (setting_name,")
    op.execute("'INSERT OR REPLACE INTO settings(name, value")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('uniswap\\\\_trades%', '\\\\'")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('sushiswap\\\\_trades%', '\\\\'")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('balancer\\\\_trades%', '\\\\'")
    op.execute("'DROP VIEW IF EXISTS combined_trades_view;'")
    op.drop_table('amm_swaps')
    op.execute('"""\n        WITH unique_assets AS (SELECT DISTINCT asset FROM(\n            SELECT currency AS asset FROM timed_balances UNION\n            SELECT asset1 AS asset FROM aave_events UNION\n            SELECT asset2 AS asset FROM aave_events UNION\n            SELECT from_asset AS asset FROM yearn_vaults_events UNION\n            SELECT to_asset AS asset FROM yearn_vaults_events UNION\n            SELECT asset FROM manually_tracked_balances UNION\n            SELECT base_asset AS asset FROM trades UNION\n            SELECT quote_asset AS asset FROM trades UNION\n            SELECT fee_currency AS asset FROM trades UNION\n            SELECT pl_currency AS asset FROM margin_positions UNION\n            SELECT fee_currency AS asset FROM margin_positions UNION\n            SELECT asset FROM asset_movements UNION\n            SELECT fee_asset AS asset FROM asset_movements UNION\n            SELECT asset FROM ledger_actions UNION\n            SELECT rate_asset AS asset FROM ledger_actions UNION\n            SELECT token0_identifier AS asset FROM amm_events UNION\n            SELECT token1_identifier AS asset FROM amm_events UNION\n            SELECT token AS asset FROM adex_events UNION\n            SELECT pool_address_token AS asset FROM balancer_events UNION\n            SELECT identifier AS asset FROM nfts UNION\n            SELECT last_price_asset AS asset FROM nfts UNION\n            SELECT asset from history_events')
    op.execute("'SELECT identifier FROM assets'")
    op.execute('"SELECT value FROM multisettings WHERE name=\'ignored_asset\';"')
    op.execute("'ALTER TABLE timed_balances RENAME COLUMN time TO timestamp'")
    op.execute("'ALTER TABLE timed_location_data RENAME COLUMN time TO timestamp'")
    op.execute("'ALTER TABLE trades RENAME COLUMN time TO timestamp'")
    op.execute("'ALTER TABLE asset_movements RENAME COLUMN time TO timestamp'")
    op.create_table('user_notes', ...)
    op.execute("'SELECT * from xpub_mappings'")
    op.create_table('xpub_mappings_copy', ...)
    op.drop_table('xpub_mappings'')
    op.execute("'ALTER TABLE xpub_mappings_copy RENAME TO xpub_mappings'")
    op.create_table('accounts_details', ...)
    op.execute("'SELECT account, tokens_list, time FROM ethereum_accounts_details'")
    op.drop_table('ethereum_accounts_details'')
    op.execute("'SELECT * FROM history_events;'")
    op.drop_table('history_events')
    op.create_table('history_events', ...)
    op.execute('insertion_query, entry')
    op.execute("'INSERT OR IGNORE INTO assets(identifier")
    op.execute('insertion_query, entry')
    op.execute('"SELECT value FROM settings WHERE name=\'current_price_oracles\'",')
    op.execute('"UPDATE settings SET value=? WHERE name=\'current_price_oracles\'",\n            (json.dumps(list_oracles_order')
    op.execute("'SELECT tx_hash from evm_tx_mappings'")
    op.execute("'SELECT parent_identifier FROM history_events_mappings WHERE value=?',\n            ('customized',")
    op.execute("'DELETE from evm_tx_mappings WHERE value !=?',\n            ('customized',")
    op.execute("'UPDATE assets SET identifier=? WHERE identifier=?', sqlite_tuples")
    op.execute('"UPDATE multisettings SET value=? WHERE value=? AND name=\'ignored_asset\'",\n            old_ids_to_caip_ids_mappings,')
    op.execute("'INSERT INTO xpub_mappings_copy VALUES (?, ?, ?, ?, ?, ?")
    op.execute("'INSERT OR IGNORE INTO accounts_details(account, blockchain, key, value")
    op.execute('insertion_query, new_entries')
    op.execute('querystr, bindings')
    op.create_table('user_notes', ...)
    op.create_table('xpub_mappings_copy', ...)
    op.create_table('accounts_details', ...)
    op.create_table('history_events', ...)
    op.create_table('user_notes', ...)
    op.create_table('accounts_details', ...)
    op.drop_table('amm_swaps')
    op.create_table('accounts_details', ...)
    op.drop_table('ethereum_accounts_details')')
    op.drop_table('history_events')
    op.create_table('accounts_details', ...)
    op.execute('UPDATE assets SET identifier=? WHERE identifier=?\', sqlite_tuples)  # noqa: E501\n\n    @progress_step(description=\'Updating ignored asset identifiers to caip format.\')\n    def _update_ignored_assets_identifiers_to_caip_format(cursor: \'DBCursor\') -> None:\n        cursor.execute("SELECT value FROM multisettings WHERE name=\'ignored_asset\';')
    op.create_table('user_notes', ...)
    op.execute('UPDATE CASCADE,\n        UNIQUE(event_identifier, sequence_index)\n        );')
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('uniswap\\\\_trades%', '\\\\'),\n        )\n        cursor.execute(\n            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('sushiswap\\\\_trades%', '\\\\'),\n        )\n        cursor.execute(\n            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('balancer\\\\_trades%', '\\\\'),\n        )\n        cursor.execute('DROP VIEW IF EXISTS combined_trades_view;")
    op.execute('DELETE FROM assets WHERE identifier NOT IN unique_assets AND identifier IS NOT NULL\n        """)\n\n    @progress_step(description=\'Renaming asset identifiers.\')\n    def _rename_assets_identifiers(write_cursor: \'DBCursor\') -> None:\n        """Version 1.26 includes the migration for the global db and the references to assets\n        need to be updated also in this database.\n        We do an update and relay on the cascade effect to update the assets\n        identifiers in the rest of the tables.\n        """\n        write_cursor.execute(\'SELECT identifier FROM assets\')\n        old_id_to_new = {}\n        for (identifier,) in write_cursor:\n            # We only need to update the ethereum assets and those that will be replaced\n            # by evm assets. Any other asset should keep the identifier they have now.\n            if identifier.startswith(ETHEREUM_DIRECTIVE):\n                old_id_to_new[identifier] = evm_address_to_identifier(\n                    address=identifier[ETHEREUM_DIRECTIVE_LENGTH:],\n                    chain_id=ChainID.ETHEREUM,\n                    token_type=EvmTokenKind.ERC20,\n                )\n            elif identifier in OTHER_EVM_CHAINS_ASSETS:\n                old_id_to_new[identifier] = OTHER_EVM_CHAINS_ASSETS[identifier]\n\n        sqlite_tuples = [(new_id, old_id) for old_id, new_id in old_id_to_new.items()]\n        log.debug(\'About to execute the asset id update with executemany\')\n        write_cursor.executemany(\'UPDATE assets SET identifier=? WHERE identifier=?\', sqlite_tuples)  # noqa: E501\n\n    @progress_step(description=\'Updating ignored asset identifiers to caip format.\')\n    def _update_ignored_assets_identifiers_to_caip_format(cursor: \'DBCursor\') -> None:\n        cursor.execute("SELECT value FROM multisettings WHERE name=\'ignored_asset\';')



def downgrade() -> None:
    """Downgrade from v35 to v34"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
