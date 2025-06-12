"""Upgrade from v43 to v44

Revision ID: 043_v43_to_v44
Revises: 042_v42_to_v43
Create Date: 2025-01-06

This upgrade includes:
- Update NFT identifiers to checksum addresses
- Remove 'removed' column from evmtx_receipt_logs
- Fix address book duplications
- Add DefiLlama to historical price oracles
- Add new ETH2 validator columns
- Add cowswap and gnosispay tables
- Reset decoded events
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '043_v43_to_v44'
down_revision = '042_v42_to_v43'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v43 to v44"""
    
    # Update NFT identifiers to use checksum addresses
    op.execute("""
        CREATE TABLE nfts_new (
            identifier TEXT NOT NULL PRIMARY KEY,
            name TEXT,
            last_price TEXT,
            last_price_asset TEXT,
            manual_price INTEGER NOT NULL CHECK(manual_price IN (0, 1)),
            owner_address TEXT,
            is_lp INTEGER NOT NULL CHECK(is_lp IN (0, 1)),
            image_url TEXT,
            collection_name TEXT,
            usd_price TEXT,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        )
    """)
    
    # Migrate NFT data with checksum addresses
    op.execute("""
        INSERT INTO nfts_new 
        SELECT 
            CASE 
                WHEN identifier LIKE '_nft_%' THEN 
                    '_nft_' || UPPER(SUBSTR(identifier, 6))
                ELSE identifier
            END,
            name, last_price, last_price_asset, manual_price, owner_address, 
            is_lp, image_url, collection_name, usd_price
        FROM nfts
    """)
    
    op.drop_table('nfts')
    op.execute("ALTER TABLE nfts_new RENAME TO nfts")
    
    # Remove 'removed' column from evmtx_receipt_logs
    op.execute("""
        CREATE TABLE evmtx_receipt_logs_new (
            tx_id INTEGER NOT NULL,
            log_index INTEGER NOT NULL,
            data BLOB NOT NULL,
            address TEXT NOT NULL,
            FOREIGN KEY(tx_id) REFERENCES evmtx_receipts(tx_id) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(tx_id, log_index)
        )
    """)
    
    op.execute("""
        INSERT INTO evmtx_receipt_logs_new (tx_id, log_index, data, address)
        SELECT tx_id, log_index, data, address FROM evmtx_receipt_logs
    """)
    
    op.drop_table('evmtx_receipt_logs')
    op.execute("ALTER TABLE evmtx_receipt_logs_new RENAME TO evmtx_receipt_logs")
    
    # Fix address book duplications (using checksum addresses)
    op.execute("""
        CREATE TEMPORARY TABLE address_book_temp AS
        SELECT MIN(object_reference) as keep_ref, 
               UPPER(object_reference) as normalized_ref,
               tag_name
        FROM tag_mappings
        WHERE object_reference LIKE '0x%' AND LENGTH(object_reference) = 42
        GROUP BY normalized_ref, tag_name
    """)
    
    op.execute("""
        DELETE FROM tag_mappings 
        WHERE object_reference IN (
            SELECT tm.object_reference
            FROM tag_mappings tm
            JOIN address_book_temp abt ON UPPER(tm.object_reference) = abt.normalized_ref
            WHERE tm.object_reference != abt.keep_ref
        )
    """)
    
    op.execute("DROP TABLE address_book_temp")
    
    # Add DefiLlama to historical price oracles if not present
    op.execute("""
        UPDATE settings 
        SET value = json_set(
            value,
            '$[' || json_array_length(value) || ']',
            'defillama'
        )
        WHERE name = 'historical_price_oracles' 
          AND value NOT LIKE '%defillama%'
    """)
    
    # Add new ETH2 validator columns
    op.add_column('eth2_validators', 
        sa.Column('withdrawable_amount', sa.TEXT, nullable=False, server_default='0')
    )
    op.add_column('eth2_validators',
        sa.Column('withdrawn_amount', sa.TEXT, nullable=False, server_default='0')
    )
    op.add_column('eth2_validators',
        sa.Column('last_update_timestamp', sa.INTEGER, nullable=False, server_default='0')
    )
    
    # Create cowswap_orders table
    op.create_table('cowswap_orders',
        sa.Column('identifier', sa.INTEGER, primary_key=True, autoincrement=True, nullable=False),
        sa.Column('order_uid', sa.TEXT, nullable=False),
        sa.Column('tx_hash', sa.BLOB),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('buy_token', sa.TEXT, nullable=False),
        sa.Column('sell_token', sa.TEXT, nullable=False),
        sa.Column('buy_amount', sa.TEXT, nullable=False),
        sa.Column('sell_amount', sa.TEXT, nullable=False),
        sa.Column('limit_buy_amount', sa.TEXT, nullable=False),
        sa.Column('limit_sell_amount', sa.TEXT, nullable=False),
        sa.Column('fee_amount', sa.TEXT, nullable=False),
        sa.Column('kind', sa.INTEGER, nullable=False),
        sa.Column('order_type', sa.INTEGER, nullable=False),
        sa.Column('app_data', sa.TEXT, nullable=False),
        sa.Column('status', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['buy_token'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['sell_token'], ['assets.identifier'], onupdate='CASCADE'),
        sa.UniqueConstraint('order_uid')
    )
    
    # Create gnosispay_data table
    op.create_table('gnosispay_data',
        sa.Column('tx_hash', sa.BLOB, primary_key=True, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('merchant_name', sa.TEXT),
        sa.Column('merchant_city', sa.TEXT),
        sa.Column('country', sa.TEXT),
        sa.Column('mcc', sa.INTEGER),
        sa.Column('transaction_symbol', sa.TEXT),
        sa.Column('transaction_amount', sa.TEXT, nullable=False),
        sa.Column('billing_symbol', sa.TEXT),
        sa.Column('billing_amount', sa.TEXT),
        sa.Column('reversal_symbol', sa.TEXT),
        sa.Column('reversal_amount', sa.TEXT),
        sa.ForeignKeyConstraint(['transaction_symbol'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['billing_symbol'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['reversal_symbol'], ['assets.identifier'], onupdate='CASCADE')
    )
    
    # Delete zksynclite query ranges
    op.execute("DELETE FROM used_query_ranges WHERE name LIKE 'zksynclitetxs\\_%' ESCAPE '\\'")
    
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
    
    # Update asset identifiers for NFTs in the assets table
    op.execute("""
        UPDATE assets 
        SET identifier = '_nft_' || UPPER(SUBSTR(identifier, 6))
        WHERE identifier LIKE '_nft_%' AND identifier != '_nft_' || UPPER(SUBSTR(identifier, 6))
    """)


def downgrade() -> None:
    """Downgrade from v44 to v43"""
    raise NotImplementedError("Downgrade not implemented for this migration")