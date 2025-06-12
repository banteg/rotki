"""Upgrade from v32 to v33

Revision ID: 032_v32_to_v33
Revises: 031_v31_to_v32
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v32_v33.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '032_v32_to_v33'
down_revision = '031_v31_to_v32'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v32 to v33"""
    # Operations ported from the original upgrade script
    op.execute("'SELECT * FROM xpub_mappings'")
    op.create_table('xpub_mappings_copy', ...)
    op.drop_table('xpub_mappings')
    op.execute("'ALTER TABLE xpub_mappings_copy RENAME TO xpub_mappings;'")
    op.create_table('address_book', ...)
    op.create_table('web3_nodes', ...)
    op.create_table('aave_events_copy', ...)
    op.execute("'SELECT * FROM aave_events'")
    op.drop_table('aave_events')
    op.execute("'ALTER TABLE aave_events_copy RENAME TO aave_events;'")
    op.create_table('adex_events_copy', ...)
    op.execute("'SELECT * FROM adex_events'")
    op.drop_table('adex_events')
    op.execute("'ALTER TABLE adex_events_copy RENAME TO adex_events;'")
    op.create_table('balancer_events_copy', ...)
    op.execute("'SELECT * FROM balancer_events'")
    op.drop_table('balancer_events')
    op.execute("'ALTER TABLE balancer_events_copy RENAME TO balancer_events;'")
    op.create_table('yearn_vaults_events_copy', ...)
    op.execute("'SELECT * FROM yearn_vaults_events'")
    op.drop_table('yearn_vaults_events')
    op.execute("'ALTER TABLE yearn_vaults_events_copy RENAME TO yearn_vaults_events;'")
    op.create_table('amm_events_copy', ...)
    op.execute("'SELECT * FROM amm_events'")
    op.drop_table('amm_events')
    op.execute("'ALTER TABLE amm_events_copy RENAME TO amm_events;'")
    op.execute("'DROP VIEW combined_trades_view;'")
    op.create_table('amm_swaps_copy', ...)
    op.execute("'SELECT * FROM amm_swaps'")
    op.drop_table('amm_swaps')
    op.execute("'ALTER TABLE amm_swaps_copy RENAME TO amm_swaps;'")
    op.execute('"""\n        CREATE VIEW combined_trades_view AS\n            WITH amounts_query AS (\n                SELECT\n                A.tx_hash AS txhash,\n                A.log_index AS logindex,\n                A.timestamp AS time,\n                A.location AS location,\n                FE.amount1_in AS first1in,\n                FE.amount0_in AS first0in,\n                FE.token0_identifier AS firsttoken0,\n                FE.token1_identifier AS firsttoken1,\n                LE.amount0_out AS last0out,\n                LE.amount1_out AS last1out,\n                LE.token0_identifier AS lasttoken0,\n                LE.token1_identifier AS lasttoken1\n                FROM amm_swaps A\n                LEFT JOIN amm_swaps FE ON\n                FE.tx_hash = A.tx_hash AND FE.log_index=(SELECT MIN(log_index')
    op.execute("'SELECT * FROM history_events_mappings'")
    op.create_table('history_events_copy', ...)
    op.execute("'SELECT * FROM history_events'")
    op.drop_table('history_events')
    op.execute("'ALTER TABLE history_events_copy RENAME TO history_events;'")
    op.execute('"UPDATE blockchain_accounts SET label = NULL WHERE label =\'\'"')
    op.execute('"""\n        INSERT INTO xpub_mappings_copy(\n            address,\n            xpub,\n            derivation_path,\n            account_index,\n            derived_index,\n            blockchain')
    op.execute("'INSERT INTO aave_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
    op.execute("'INSERT INTO adex_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
    op.execute("'INSERT INTO balancer_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
    op.execute("'INSERT INTO yearn_vaults_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
    op.execute("'INSERT INTO amm_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
    op.execute("'INSERT INTO amm_swaps_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
    op.execute("'INSERT INTO history_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
    op.execute("'INSERT INTO history_events_mappings(parent_identifier, value")
    op.create_table('xpub_mappings_copy', ...)
    op.create_table('address_book', ...)
    op.create_table('web3_nodes', ...)
    op.create_table('aave_events_copy', ...)
    op.create_table('adex_events_copy', ...)
    op.create_table('balancer_events_copy', ...)
    op.create_table('yearn_vaults_events_copy', ...)
    op.create_table('amm_events_copy', ...)
    op.create_table('amm_swaps_copy', ...)
    op.create_table('history_events_copy', ...)
    op.execute('ALTER TABLE xpub_mappings_copy RENAME TO xpub_mappings;')
    op.execute('ALTER TABLE aave_events_copy RENAME TO aave_events;')
    op.execute('ALTER TABLE adex_events_copy RENAME TO adex_events;')
    op.execute('ALTER TABLE balancer_events_copy RENAME TO balancer_events;')
    op.execute('ALTER TABLE yearn_vaults_events_copy RENAME TO yearn_vaults_events;')
    op.execute('ALTER TABLE amm_events_copy RENAME TO amm_events;')
    op.execute('ALTER TABLE amm_swaps_copy RENAME TO amm_swaps;')
    op.execute('ALTER TABLE history_events_copy RENAME TO history_events;')
    op.drop_table('xpub_mappings')
    op.drop_table('aave_events')
    op.drop_table('adex_events')
    op.drop_table('balancer_events')
    op.drop_table('yearn_vaults_events')
    op.drop_table('amm_events')
    op.drop_table('amm_swaps')
    op.drop_table('history_events')
    op.execute('INSERT INTO xpub_mappings_copy(\n            address,\n            xpub,\n            derivation_path,\n            account_index,\n            derived_index,\n            blockchain\n        )\n        VALUES(?, ?, ?, ?, ?, ?);')
    op.execute("INSERT INTO aave_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);")
    op.execute("INSERT INTO adex_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);")
    op.execute("INSERT INTO balancer_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);")
    op.execute("INSERT INTO yearn_vaults_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);")
    op.execute("INSERT INTO amm_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);")
    op.execute("INSERT INTO amm_swaps_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);")
    op.execute("INSERT INTO history_events_copy VALUES'\n            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);")
    op.execute('INSERT INTO history_events_mappings(parent_identifier, value) VALUES(?, ?);')
    op.execute('UPDATE CASCADE,\n            FOREIGN KEY(asset2) REFERENCES assets(identifier) ON UPDATE CASCADE,\n            PRIMARY KEY (event_type, tx_hash, log_index)\n        );')
    op.execute('UPDATE CASCADE,\n            PRIMARY KEY (tx_hash, address, type, log_index)\n        );')
    op.execute('UPDATE CASCADE,\n            PRIMARY KEY (tx_hash, log_index)\n        );')
    op.execute('UPDATE CASCADE,\n            FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,\n            PRIMARY KEY (event_type, tx_hash, log_index)\n        );')
    op.execute('UPDATE CASCADE,\n            FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,\n            PRIMARY KEY (tx_hash, log_index)\n        );')
    op.execute('UPDATE CASCADE,\n            FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,\n            PRIMARY KEY (tx_hash, log_index)\n        );')



def downgrade() -> None:
    """Downgrade from v33 to v32"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
