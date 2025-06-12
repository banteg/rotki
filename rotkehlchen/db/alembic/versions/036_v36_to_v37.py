"""Upgrade from v36 to v37

Revision ID: 036_v36_to_v37
Revises: 035_v35_to_v36
Create Date: 2025-01-06

This upgrade includes:
- Reset decoded events for EVM transactions
- Update ENS name cache table
- Update history events table structure
- Recalculate validator daily stats for ETH2
- Fix Kraken events with negative amounts
- Remove FTX data
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '036_v36_to_v37'
down_revision = '035_v35_to_v36'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v36 to v37"""
    
    # Add new locations for Ethereum and Optimism
    op.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('f', 38)")
    op.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('g', 39)")
    
    # Reset decoded events by removing all EVM transaction mappings except customized ones
    op.execute("""
        DELETE FROM evm_tx_mappings 
        WHERE value = 0 AND tx_hash NOT IN (
            SELECT DISTINCT he.event_identifier
            FROM history_events he
            JOIN history_events_mappings hem ON he.identifier = hem.parent_identifier
            WHERE hem.name = 'customized' AND hem.value = 1
        )
    """)
    
    # Create evm_events_info table
    op.create_table('evm_events_info',
        sa.Column('identifier', sa.INTEGER, nullable=False),
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('counterparty', sa.TEXT),
        sa.Column('product', sa.TEXT),
        sa.Column('address', sa.TEXT),
        sa.ForeignKeyConstraint(['identifier'], ['history_events.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('identifier')
    )
    
    # Create eth_staking_events_info table
    op.create_table('eth_staking_events_info',
        sa.Column('identifier', sa.INTEGER, nullable=False),
        sa.Column('validator_index', sa.INTEGER, nullable=False),
        sa.Column('is_exit_or_blocknumber', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['identifier'], ['history_events.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['validator_index'], ['eth2_validators.validator_index'], onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('identifier')
    )
    
    # Update history_events table structure
    op.execute("""
        CREATE TABLE history_events_copy (
            identifier INTEGER PRIMARY KEY NOT NULL,
            entry_type INTEGER NOT NULL,
            event_identifier TEXT NOT NULL,
            sequence_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            location CHAR(1) NOT NULL DEFAULT 'A',
            location_label TEXT,
            asset TEXT NOT NULL,
            amount TEXT NOT NULL,
            usd_value TEXT NOT NULL,
            notes TEXT,
            type TEXT NOT NULL,
            subtype TEXT,
            FOREIGN KEY(location) REFERENCES location(location),
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            UNIQUE(event_identifier, sequence_index)
        )
    """)
    
    # Migrate data from history_events to history_events_copy with new entry_type column
    op.execute("""
        INSERT INTO history_events_copy 
        SELECT identifier, 1, event_identifier, sequence_index, timestamp, location,
               location_label, asset, amount, usd_value, notes, type, subtype
        FROM history_events
    """)
    
    # Extract EVM events info
    op.execute("""
        INSERT INTO evm_events_info (identifier, tx_hash, chain_id)
        SELECT he.identifier, et.tx_hash, et.chain_id
        FROM history_events he
        JOIN evm_transactions et ON he.event_identifier = et.tx_hash
        WHERE he.location IN ('f', 'g')
    """)
    
    op.drop_table('history_events')
    op.execute("ALTER TABLE history_events_copy RENAME TO history_events")
    
    # Update ENS mappings schema
    op.execute("""
        CREATE TABLE ens_mappings_new (
            address TEXT NOT NULL PRIMARY KEY,
            ens_name TEXT UNIQUE,
            last_update INTEGER NOT NULL,
            last_avatar_update INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    op.execute("""
        INSERT INTO ens_mappings_new (address, ens_name, last_update)
        SELECT address, ens_name, last_update FROM ens_mappings
    """)
    
    op.drop_table('ens_mappings')
    op.execute("ALTER TABLE ens_mappings_new RENAME TO ens_mappings")
    
    # Delete old tables
    op.drop_table('eth2_deposits')
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'eth2_deposits%'")
    
    # Fix Kraken events
    # Fix staking ETH after merge with negative amounts
    op.execute("""
        UPDATE history_events 
        SET type = 'informational', 
            subtype = 'none',
            amount = ABS(CAST(amount AS REAL)),
            usd_value = ABS(CAST(usd_value AS REAL)),
            notes = 'Automatic virtual conversion of staked ETH rewards to ETH'
        WHERE location = 'B' 
          AND asset = 'ETH2' 
          AND type = 'staking' 
          AND subtype = 'reward' 
          AND CAST(amount AS REAL) < 0
    """)
    
    # Fix Kraken trades without subtypes
    op.execute("""
        UPDATE history_events 
        SET subtype = CASE 
            WHEN CAST(amount AS REAL) < 0 THEN 'spend'
            ELSE 'receive'
        END,
        amount = ABS(CAST(amount AS REAL)),
        usd_value = ABS(CAST(usd_value AS REAL))
        WHERE location = 'B' 
          AND type = 'trade' 
          AND subtype = 'none'
    """)
    
    # Fix Kraken withdrawals (should have negative amounts)
    op.execute("""
        UPDATE history_events 
        SET amount = -ABS(CAST(amount AS REAL)),
            usd_value = -ABS(CAST(usd_value AS REAL))
        WHERE location = 'B' AND type = 'withdrawal'
    """)
    
    # Fix Kraken instant swaps
    op.execute("""
        UPDATE history_events 
        SET type = 'trade',
            subtype = CASE 
                WHEN type = 'spend' THEN 'spend'
                ELSE 'receive'
            END,
            amount = CASE 
                WHEN type = 'spend' THEN -ABS(CAST(amount AS REAL))
                ELSE ABS(CAST(amount AS REAL))
            END,
            usd_value = CASE 
                WHEN type = 'spend' THEN -ABS(CAST(usd_value AS REAL))
                ELSE ABS(CAST(usd_value AS REAL))
            END
        WHERE location = 'B' 
          AND type IN ('spend', 'receive') 
          AND subtype = 'none'
    """)
    
    # Trim daily stats
    op.execute("""
        CREATE TABLE eth2_daily_staking_details_new (
            validator_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            pnl TEXT NOT NULL,
            FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY (validator_index, timestamp)
        )
    """)
    
    op.execute("""
        INSERT INTO eth2_daily_staking_details_new (validator_index, timestamp, pnl)
        SELECT validator_index, timestamp, pnl
        FROM eth2_daily_staking_details
        WHERE start_amount != 0 OR end_amount != 0 OR amount_deposited != 0
    """)
    
    op.drop_table('eth2_daily_staking_details')
    op.execute("ALTER TABLE eth2_daily_staking_details_new RENAME TO eth2_daily_staking_details")
    
    # Remove FTX data
    op.execute("DELETE FROM user_credentials WHERE location IN ('T', 'U')")
    op.execute("DELETE FROM user_credentials_mappings WHERE credential_location IN ('T', 'U')")
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'ftx\\_%' ESCAPE '\\'")
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'ftxus\\_%' ESCAPE '\\'")
    
    # Update non-syncing exchanges setting
    op.execute("""
        UPDATE settings 
        SET value = REPLACE(REPLACE(value, '"ftx",', ''), ',"ftx"', '')
        WHERE name = 'non_syncing_exchanges' AND value LIKE '%ftx%'
    """)
    
    op.execute("""
        UPDATE settings 
        SET value = REPLACE(REPLACE(value, '"ftxus",', ''), ',"ftxus"', '')
        WHERE name = 'non_syncing_exchanges' AND value LIKE '%ftxus%'
    """)
    
    # Fix typo in setting name
    op.execute("UPDATE settings SET name='ssf_graph_multiplier' WHERE name='ssf_0graph_multiplier'")


def downgrade() -> None:
    """Downgrade from v37 to v36"""
    raise NotImplementedError("Downgrade not implemented for this migration")