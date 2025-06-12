"""Upgrade from v30 to v31

Revision ID: 030_v30_to_v31
Revises: 029_v29_to_v30
Create Date: 2025-01-06

This upgrade includes:
- Delete ignored ethereum transaction ids
- Delete kraken trades and query ranges
- Update eth2 tables with foreign keys
- Create combined_trades_view
- Create history_events table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '030_v30_to_v31'
down_revision = '029_v29_to_v30'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v30 to v31"""
    
    # Check if ignored_actions exists and delete ethereum tx ids
    conn = op.get_bind()
    result = conn.exec_driver_sql(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='ignored_actions'"
    ).fetchone()
    
    if result and result[0] == 1:
        op.execute("DELETE FROM ignored_actions WHERE type='C'")
    else:
        # Create the table if it doesn't exist
        op.create_table('ignored_actions',
            sa.Column('type', sa.CHAR(1), nullable=False, server_default='A'),
            sa.Column('identifier', sa.TEXT),
            sa.PrimaryKeyConstraint('type', 'identifier')
        )
    
    # Delete kraken trades and query ranges
    op.execute("DELETE FROM trades WHERE location='B'")
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'kraken\\_trades\\_%' ESCAPE '\\'")
    
    # Update eth2 tables
    op.execute('DROP TABLE IF EXISTS eth2_deposits')
    op.execute('DROP TABLE IF EXISTS eth2_daily_staking_details')
    
    op.create_table('eth2_validators',
        sa.Column('validator_index', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('public_key', sa.TEXT, nullable=False, unique=True),
        sa.Column('ownership_proportion', sa.TEXT, nullable=False)
    )
    
    op.create_table('eth2_deposits',
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('tx_index', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.VARCHAR(42), nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('pubkey', sa.TEXT, nullable=False),
        sa.Column('withdrawal_credentials', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT, nullable=False),
        sa.Column('usd_value', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['pubkey'], ['eth2_validators.public_key'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tx_hash', 'pubkey', 'amount')
    )
    
    op.create_table('eth2_daily_staking_details',
        sa.Column('validator_index', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('start_usd_price', sa.TEXT, nullable=False),
        sa.Column('end_usd_price', sa.TEXT, nullable=False),
        sa.Column('pnl', sa.TEXT, nullable=False),
        sa.Column('start_amount', sa.TEXT, nullable=False),
        sa.Column('end_amount', sa.TEXT, nullable=False),
        sa.Column('missed_attestations', sa.INTEGER),
        sa.Column('orphaned_attestations', sa.INTEGER),
        sa.Column('proposed_blocks', sa.INTEGER),
        sa.Column('missed_blocks', sa.INTEGER),
        sa.Column('orphaned_blocks', sa.INTEGER),
        sa.Column('included_attester_slashings', sa.INTEGER),
        sa.Column('proposer_attester_slashings', sa.INTEGER),
        sa.Column('deposits_number', sa.INTEGER),
        sa.Column('amount_deposited', sa.TEXT),
        sa.ForeignKeyConstraint(['validator_index'], ['eth2_validators.validator_index'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('validator_index', 'timestamp')
    )
    
    # Create combined_trades_view
    op.execute("""
CREATE VIEW IF NOT EXISTS combined_trades_view AS
    WITH amounts_query AS (
        SELECT
        A.tx_hash AS txhash,
        A.log_index AS logindex,
        A.timestamp AS time,
        A.location AS location,
        FE.amount1_in AS first1in,
        FE.amount0_in AS first0in,
        FE.token0_identifier AS firsttoken0,
        FE.token1_identifier AS firsttoken1,
        LE.amount0_out AS last0out,
        LE.amount1_out AS last1out,
        LE.token0_identifier AS lasttoken0,
        LE.token1_identifier AS lasttoken1
        FROM amm_swaps A
        LEFT JOIN amm_swaps FE ON
        FE.tx_hash = A.tx_hash AND FE.log_index=(SELECT MIN(log_index) FROM amm_swaps WHERE tx_hash=A.tx_hash)
        LEFT JOIN amm_swaps LE ON
        LE.tx_hash = A.tx_hash AND LE.log_index=(SELECT MAX(log_index) FROM amm_swaps WHERE tx_hash=A.tx_hash)
        WHERE A.tx_hash IN (SELECT DISTINCT tx_hash FROM amm_swaps) GROUP BY A.tx_hash
    ), C1 AS (
        SELECT lasttoken0 AS base1, firsttoken0 AS quote1, last0out AS amount1, cast(first0in AS REAL) / CAST(last0out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first0in > 0 AND last0out > 0 AND first1in == 0 AND last1out == 0
    ), C2 AS (
        SELECT lasttoken1 AS base1, firsttoken0 AS quote1, last1out AS amount1, cast(first0in AS REAL) / CAST(last1out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first0in > 0 AND last1out > 0 AND first1in == 0 AND last0out == 0
    ), C3 AS (
        SELECT lasttoken0 AS base1, firsttoken1 AS quote1, last0out AS amount1, CAST(first1in AS REAL) / CAST(last0out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND last0out > 0 AND first0in == 0 AND last1out == 0
    ), C4 AS (
        SELECT lasttoken1 AS base1, firsttoken1 AS quote1, last1out AS amount1, CAST(first1in AS REAL) / CAST(last1out AS REAL) AS rate1, txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND last1out > 0 AND first0in == 0 AND last0out == 0
    ), C5 AS (
        SELECT
            lasttoken1 AS base1,
            firsttoken1 AS quote1,
            (CAST(last1out AS REAL) / 2) AS amount1,
            CAST(first1in AS REAL) / (CAST(last1out AS REAL) / 2) as rate1,
            lasttoken1 AS base2,
            firsttoken0 AS quote2,
            (CAST(last1out AS REAL) / 2) AS amount2,
            CAST(first0in AS REAL) / (CAST(last1out AS REAL) / 2) AS rate2,
            txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND first0in > 0 AND last1out > 0 AND last0out == 0
    ), C6 AS (
        SELECT
            lasttoken1 AS base1,
            firsttoken1 AS quote1,
            last1out AS amount1,
            CAST(first1in AS REAL) / CAST(last1out AS REAL) AS rate1,
            lasttoken0 AS base2,
            firsttoken0 AS quote2,
            last0out AS amount2,
            CAST(first0in AS REAL) / CAST(last0out AS REAL) AS rate2,
            txhash, logindex, time, location
        FROM amounts_query
        WHERE first1in > 0 AND first0in > 0 AND last1out > 0 AND last0out > 0
    ), SWAPS AS (
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C1
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C2
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C3
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C4
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C5
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base2 AS base_asset, quote2 AS quote_asset, amount2 AS amount, rate2 AS rate, txhash, logindex, time, location FROM C5
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C6
    UNION ALL /* using union all as there can be no duplicates so no need to handle them */
    SELECT base2 AS base_asset, quote2 AS quote_asset, amount2 AS amount, rate2 AS rate, txhash, logindex, time, location FROM C6
)
SELECT
    txhash + logindex AS id,
    time,
    location,
    base_asset,
    quote_asset,
    'A' AS type, /* always a BUY */
    amount,
    rate,
    NULL AS fee, /* no fee */
    NULL AS fee_currency, /* no fee */
    txhash AS link,
    NULL AS notes /* no notes */
FROM SWAPS
UNION ALL /* using union all as there can be no duplicates so no need to handle them */
SELECT * from trades
""")
    
    # Create history_events table
    op.create_table('history_events',
        sa.Column('identifier', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('event_identifier', sa.TEXT, nullable=False),
        sa.Column('sequence_index', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('location', sa.TEXT, nullable=False),
        sa.Column('location_label', sa.TEXT),
        sa.Column('asset', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT, nullable=False),
        sa.Column('usd_value', sa.TEXT, nullable=False),
        sa.Column('notes', sa.TEXT),
        sa.Column('type', sa.TEXT, nullable=False),
        sa.Column('subtype', sa.TEXT)
    )


def downgrade() -> None:
    """Downgrade from v31 to v30"""
    raise NotImplementedError("Downgrade not implemented for this migration")