"""Upgrade from v45 to v46

Revision ID: 045_v45_to_v46
Revises: 044_v44_to_v45
Create Date: 2025-01-06

This upgrade includes:
- Remove balancer from active modules
- Add extra_data column to history_events
- Migrate asset_movements to history_events
- Remove asset_movements and asset_movement_category tables
- Reset decoded events
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '045_v45_to_v46'
down_revision = '044_v44_to_v45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v45 to v46"""
    
    # Remove balancer from active modules
    op.execute("""
        UPDATE settings 
        SET value = json_remove(
            value,
            '$[' || (
                SELECT key FROM json_each(value) 
                WHERE json_each.value = 'balancer'
            ) || ']'
        )
        WHERE name = 'active_modules' 
          AND value LIKE '%"balancer"%'
    """)
    
    # Add extra_data column to history_events
    op.add_column('history_events',
        sa.Column('extra_data', sa.TEXT)
    )
    
    # Migrate extra_data from evm_events_info to history_events
    op.execute("""
        UPDATE history_events 
        SET extra_data = (
            SELECT extra_data 
            FROM evm_events_info 
            WHERE evm_events_info.identifier = history_events.identifier
        )
        WHERE EXISTS (
            SELECT 1 FROM evm_events_info 
            WHERE evm_events_info.identifier = history_events.identifier
        )
    """)
    
    # Drop extra_data column from evm_events_info
    op.execute("""
        CREATE TABLE evm_events_info_new (
            identifier INTEGER NOT NULL,
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            counterparty TEXT,
            product TEXT,
            address TEXT,
            FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(identifier)
        )
    """)
    
    op.execute("""
        INSERT INTO evm_events_info_new (identifier, tx_hash, chain_id, counterparty, product, address)
        SELECT identifier, tx_hash, chain_id, counterparty, product, address
        FROM evm_events_info
    """)
    
    op.drop_table('evm_events_info')
    op.execute("ALTER TABLE evm_events_info_new RENAME TO evm_events_info")
    
    # Migrate asset_movements to history_events
    # First delete existing history events linked to asset movements
    op.execute("""
        DELETE FROM history_events 
        WHERE event_identifier IN (
            SELECT link FROM asset_movements 
            WHERE location = 'J'  -- Kraken
        )
    """)
    
    # Insert asset movements as history events
    op.execute("""
        INSERT OR IGNORE INTO history_events(
            entry_type, event_identifier, sequence_index, timestamp, location, 
            location_label, asset, amount, usd_value, notes, type, subtype, extra_data
        )
        SELECT 
            CASE 
                WHEN category = 'A' THEN 1  -- deposit
                ELSE 1  -- withdrawal
            END as entry_type,
            COALESCE(link, 'AM_' || id) as event_identifier,
            0 as sequence_index,
            timestamp,
            location,
            address as location_label,
            asset,
            CASE 
                WHEN category = 'A' THEN amount  -- deposit: positive
                ELSE '-' || amount  -- withdrawal: negative
            END as amount,
            '0' as usd_value,
            'Migrated from asset movements' as notes,
            CASE 
                WHEN category = 'A' THEN 'deposit'
                ELSE 'withdrawal'
            END as type,
            'none' as subtype,
            json_object(
                'transaction_id', transaction_id,
                'fee', fee,
                'fee_asset', fee_asset
            ) as extra_data
        FROM asset_movements
    """)
    
    # Drop asset_movements related tables
    op.drop_table('asset_movements')
    op.drop_table('asset_movement_category')
    
    # Remove account_for_assets_movements setting
    op.execute("DELETE FROM settings WHERE name='account_for_assets_movements'")
    
    # Reset decoded events except customized ones
    op.execute("""
        DELETE FROM evm_tx_mappings 
        WHERE tx_id IN (
            SELECT tx_id FROM evm_transactions
        ) AND value = 0 AND tx_id NOT IN (
            SELECT DISTINCT et.tx_id
            FROM history_events he
            JOIN evm_transactions et ON he.event_identifier = et.tx_hash
            JOIN history_events_mappings hem ON he.identifier = hem.parent_identifier
            WHERE hem.name = 'customized' AND hem.value = 1
        )
    """)


def downgrade() -> None:
    """Downgrade from v46 to v45"""
    raise NotImplementedError("Downgrade not implemented for this migration")