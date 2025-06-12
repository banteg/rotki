"""Upgrade from v37 to v38

Revision ID: 037_v37_to_v38
Revises: 036_v36_to_v37
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v37_v38.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '037_v37_to_v38'
down_revision = '036_v36_to_v37'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v37 to v38"""
    # Operations ported from the original upgrade script
    op.execute('"INSERT OR IGNORE INTO location(location, seq')
    op.drop_table('aave_events')
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('aave\\\\_events%', '\\\\'")
    op.drop_table('amm_events')
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('uniswap\\\\_events\\\\_%', '\\\\'")
    op.execute("'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',\n            ('sushiswap\\\\_events\\\\_%', '\\\\'")
    op.execute("'SELECT COUNT(*")
    op.execute("'SELECT COUNT(*")
    op.execute('querystr, bindings')
    op.execute("'DELETE from evm_tx_mappings WHERE tx_hash IN (SELECT tx_hash FROM evm_transactions")
    op.execute('"DELETE FROM history_events WHERE identifier IN ("\n            "SELECT B.identifier from history_events A INNER JOIN history_events B "\n            "ON A.event_identifier=B.event_identifier AND A.subtype=\'block production\' "\n            "AND B.subtype=\'mev reward\' AND A.amount=B.amount WHERE A.entry_type=4')
    op.execute("'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain")
    op.drop_table('aave_events')
    op.drop_table('amm_events')
    op.drop_table('aave_events')
    op.drop_table('aave_events')
    op.drop_table('amm_events')
    op.execute('DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?\',\n            (\'uniswap\\\\_events\\\\_%\', \'\\\\\'),\n        )\n        write_cursor.execute(\n            \'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?\',\n            (\'sushiswap\\\\_events\\\\_%\', \'\\\\\'),\n        )\n\n    @progress_step(description=\'Resetting decoded events.\')\n    def _reset_decoded_events(write_cursor: \'DBCursor\') -> None:\n        """\n        Reset all decoded evm events except the customized ones for ethereum mainnet and optimism.\n        """\n        if write_cursor.execute(\'SELECT COUNT(*) FROM evm_transactions\').fetchone()[0] == 0:\n            return\n\n        customized_events = write_cursor.execute(\n            \'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?\',\n            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),\n        ).fetchone()[0]\n        querystr = (\n            \'DELETE FROM history_events WHERE identifier IN (\'\n            \'SELECT H.identifier from history_events H INNER JOIN evm_events_info E \'\n            \'ON H.identifier=E.identifier AND E.tx_hash IN \'\n            \'(SELECT tx_hash FROM evm_transactions))\'\n        )\n        bindings: tuple = ()\n        if customized_events != 0:\n            querystr += \' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)\'  # noqa: E501\n            bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)\n\n        write_cursor.execute(querystr, bindings)\n        write_cursor.execute(\n            \'DELETE from evm_tx_mappings WHERE tx_hash IN (SELECT tx_hash FROM evm_transactions) AND value=?\',  # noqa: E501\n            (0,),  # decoded tx state\n        )\n\n    @progress_step(description=\'Removing duplicate block mev rewards.\')\n    def _remove_duplicate_block_mev_rewards(write_cursor: \'DBCursor\') -> None:\n        """If mev reward is exact same as block production reward then it\'s a duplicate event.\n        In that case it needs to be deleted.\n        """\n        write_cursor.execute(\n            "DELETE FROM history_events WHERE identifier IN ("\n            "SELECT B.identifier from history_events A INNER JOIN history_events B "\n            "ON A.event_identifier=B.event_identifier AND A.subtype=\'block production\' "\n            "AND B.subtype=\'mev reward\' AND A.amount=B.amount WHERE A.entry_type=4);')



def downgrade() -> None:
    """Downgrade from v38 to v37"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
