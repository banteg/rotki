"""Initial Alembic migration representing v48 schema

Revision ID: 001_initial_v48
Revises: 
Create Date: 2025-01-06

This migration creates the complete database schema as of v48.
It serves as the base for transitioning from the old upgrade system to Alembic.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_v48'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables for v48 schema"""
    
    # Create enum tables first
    op.create_table('location',
        sa.Column('location', sa.CHAR(1), primary_key=True, nullable=False),
        sa.Column('seq', sa.INTEGER, unique=True)
    )
    
    op.create_table('balance_category',
        sa.Column('category', sa.CHAR(1), primary_key=True, nullable=False),
        sa.Column('seq', sa.INTEGER, unique=True)
    )
    
    op.create_table('zksynclite_tx_type',
        sa.Column('type', sa.CHAR(1), primary_key=True, nullable=False),
        sa.Column('seq', sa.INTEGER, unique=True)
    )
    
    # Insert location enum values
    locations = [
        ('A', 1, 'External'), ('B', 2, 'Kraken'), ('C', 3, 'Poloniex'), 
        ('D', 4, 'Bittrex'), ('E', 5, 'Binance'), ('F', 6, 'Bitmex'),
        ('G', 7, 'Coinbase'), ('H', 8, 'Total'), ('I', 9, 'Banks'),
        ('J', 10, 'Blockchain'), ('K', 11, 'Coinbase Pro'), ('L', 12, 'Gemini'),
        ('M', 13, 'Equities'), ('N', 14, 'Real estate'), ('O', 15, 'Commodities'),
        ('P', 16, 'Crypto.com'), ('Q', 17, 'Uniswap'), ('R', 18, 'Bitstamp'),
        ('S', 19, 'Binance US'), ('T', 20, 'Bitfinex'), ('U', 21, 'Bitcoin.de'),
        ('V', 22, 'ICONOMI'), ('W', 23, 'KUCOIN'), ('X', 24, 'BALANCER'),
        ('Y', 25, 'LOOPRING'), ('Z', 26, 'FTX'), ('[', 27, 'NEXO'),
        ('\\\\', 28, 'BlockFI'), (']', 29, 'IndependentReserve'), ('^', 30, 'Gitcoin'),
        ('_', 31, 'Sushiswap'), ('`', 32, 'ShapeShift'), ('a', 33, 'Uphold'),
        ('b', 34, 'Bitpanda'), ('c', 35, 'Bisq'), ('d', 36, 'FTX US'),
        ('e', 37, 'OKX'), ('f', 38, 'ETHEREUM'), ('g', 39, 'OPTIMISM'),
        ('h', 40, 'POLYGON_POS'), ('i', 41, 'ARBITRUM_ONE'), ('j', 42, 'BASE'),
        ('k', 43, 'GNOSIS'), ('l', 44, 'WOO'), ('m', 45, 'Bybit'),
        ('n', 46, 'Scroll'), ('o', 47, 'ZKSync Lite'), ('p', 48, 'HTX'),
        ('q', 49, 'Bitcoin'), ('r', 50, 'Bitcoin Cash'), ('s', 51, 'Polkadot'),
        ('t', 52, 'Kusama'), ('u', 53, 'Coinbase Prime'), ('v', 54, 'Binance Smart Chain')
    ]
    
    for loc, seq, _ in locations:
        op.execute(f"INSERT INTO location(location, seq) VALUES ('{loc}', {seq})")
    
    # Insert balance_category enum values
    op.execute("INSERT INTO balance_category(category, seq) VALUES ('A', 1)")  # Asset
    op.execute("INSERT INTO balance_category(category, seq) VALUES ('B', 2)")  # Liability
    
    # Insert zksynclite_tx_type enum values
    zksync_types = [
        ('A', 1, 'Transfer'), ('B', 2, 'Deposit'), ('C', 3, 'Withdraw'),
        ('D', 4, 'ChangePubKey'), ('E', 5, 'ForcedExit'), ('F', 6, 'FullExit'),
        ('G', 7, 'Swap')
    ]
    
    for tx_type, seq, _ in zksync_types:
        op.execute(f"INSERT INTO zksynclite_tx_type(type, seq) VALUES ('{tx_type}', {seq})")
    
    # Create core tables
    op.create_table('assets',
        sa.Column('identifier', sa.TEXT, primary_key=True, nullable=False)
    )
    
    op.create_table('settings',
        sa.Column('name', sa.VARCHAR(24), primary_key=True, nullable=False),
        sa.Column('value', sa.TEXT)
    )
    
    op.create_table('tags',
        sa.Column('name', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('description', sa.TEXT),
        sa.Column('background_color', sa.TEXT),
        sa.Column('foreground_color', sa.TEXT)
    )
    
    op.create_table('blockchain_accounts',
        sa.Column('blockchain', sa.VARCHAR(24), primary_key=True, nullable=False),
        sa.Column('account', sa.TEXT, primary_key=True, nullable=False)
    )
    
    op.create_table('ignored_actions',
        sa.Column('identifier', sa.TEXT, primary_key=True)
    )
    
    # Create tables with foreign keys
    op.create_table('tag_mappings',
        sa.Column('object_reference', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('tag_name', sa.TEXT, primary_key=True, nullable=False),
        sa.ForeignKeyConstraint(['tag_name'], ['tags.name'])
    )
    
    op.create_table('timed_balances',
        sa.Column('timestamp', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('currency', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('category', sa.CHAR(1), primary_key=True, nullable=False, server_default='A'),
        sa.Column('amount', sa.TEXT),
        sa.Column('usd_value', sa.TEXT),
        sa.ForeignKeyConstraint(['currency'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['category'], ['balance_category.category'])
    )
    
    op.create_table('timed_location_data',
        sa.Column('timestamp', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('location', sa.CHAR(1), primary_key=True, nullable=False, server_default='A'),
        sa.Column('usd_value', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location'])
    )
    
    op.create_table('user_credentials',
        sa.Column('name', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('location', sa.CHAR(1), primary_key=True, nullable=False, server_default='A'),
        sa.Column('api_key', sa.TEXT),
        sa.Column('api_secret', sa.TEXT),
        sa.Column('passphrase', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location'])
    )
    
    op.create_table('user_credentials_mappings',
        sa.Column('credential_name', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('credential_location', sa.CHAR(1), primary_key=True, nullable=False, server_default='A'),
        sa.Column('setting_name', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('setting_value', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(
            ['credential_name', 'credential_location'],
            ['user_credentials.name', 'user_credentials.location'],
            ondelete='CASCADE',
            onupdate='CASCADE'
        )
    )
    
    op.create_table('external_service_credentials',
        sa.Column('name', sa.VARCHAR(30), primary_key=True, nullable=False),
        sa.Column('api_key', sa.TEXT, nullable=False),
        sa.Column('api_secret', sa.TEXT)
    )
    
    op.create_table('manually_tracked_balances',
        sa.Column('id', sa.INTEGER, primary_key=True),
        sa.Column('asset', sa.TEXT, nullable=False),
        sa.Column('label', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('category', sa.CHAR(1), nullable=False, server_default='A'),
        sa.ForeignKeyConstraint(['asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['location'], ['location.location']),
        sa.ForeignKeyConstraint(['category'], ['balance_category.category'])
    )
    
    op.create_table('multisettings',
        sa.Column('name', sa.VARCHAR(24), nullable=False),
        sa.Column('value', sa.TEXT),
        sa.UniqueConstraint('name', 'value')
    )
    
    # EVM tables
    op.create_table('evm_transactions',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('chain_id', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('block_number', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.Column('gas', sa.TEXT, nullable=False),
        sa.Column('gas_price', sa.TEXT, nullable=False),
        sa.Column('gas_used', sa.TEXT, nullable=False),
        sa.Column('input_data', sa.BLOB, nullable=False),
        sa.Column('nonce', sa.INTEGER, nullable=False),
        sa.UniqueConstraint('tx_hash', 'chain_id')
    )
    
    op.create_table('evm_internal_transactions',
        sa.Column('parent_tx', sa.INTEGER, nullable=False),
        sa.Column('trace_id', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('value', sa.TEXT, nullable=False),
        sa.Column('gas', sa.TEXT, nullable=False),
        sa.Column('gas_used', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['parent_tx'], ['evm_transactions.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('parent_tx', 'trace_id', 'from_address', 'to_address', 'value', 'gas', 'gas_used')
    )
    
    op.create_table('evmtx_receipts',
        sa.Column('tx_id', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('contract_address', sa.TEXT),
        sa.Column('status', sa.INTEGER, nullable=False),
        sa.Column('type', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_id'], ['evm_transactions.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.CheckConstraint('status IN (0, 1)')
    )
    
    op.create_table('evmtx_receipt_logs',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('tx_id', sa.INTEGER, nullable=False),
        sa.Column('log_index', sa.INTEGER, nullable=False),
        sa.Column('data', sa.BLOB, nullable=False),
        sa.Column('address', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['tx_id'], ['evmtx_receipts.tx_id'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.UniqueConstraint('tx_id', 'log_index')
    )
    
    op.create_table('evmtx_receipt_log_topics',
        sa.Column('log', sa.INTEGER, nullable=False),
        sa.Column('topic', sa.BLOB, nullable=False),
        sa.Column('topic_index', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['log'], ['evmtx_receipt_logs.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('log', 'topic_index')
    )
    
    op.create_table('evmtx_address_mappings',
        sa.Column('tx_id', sa.INTEGER, nullable=False),
        sa.Column('address', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['tx_id'], ['evm_transactions.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_id', 'address')
    )
    
    op.create_table('evm_tx_mappings',
        sa.Column('tx_id', sa.INTEGER, nullable=False),
        sa.Column('value', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['tx_id'], ['evm_transactions.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('tx_id', 'value')
    )
    
    op.create_table('optimism_transactions',
        sa.Column('tx_id', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('l1_fee', sa.TEXT),
        sa.ForeignKeyConstraint(['tx_id'], ['evm_transactions.identifier'], ondelete='CASCADE', onupdate='CASCADE')
    )
    
    op.create_table('evm_transactions_authorizations',
        sa.Column('tx_id', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('nonce', sa.INTEGER, nullable=False),
        sa.Column('delegated_address', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['tx_id'], ['evm_transactions.identifier'], ondelete='CASCADE')
    )
    
    op.create_table('evm_accounts_details',
        sa.Column('account', sa.VARCHAR(42), primary_key=True, nullable=False),
        sa.Column('chain_id', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('key', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('value', sa.TEXT, primary_key=True, nullable=False)
    )
    
    # History events
    op.create_table('history_events',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('entry_type', sa.INTEGER, nullable=False),
        sa.Column('event_identifier', sa.TEXT, nullable=False),
        sa.Column('sequence_index', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('location_label', sa.TEXT),
        sa.Column('asset', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT, nullable=False),
        sa.Column('notes', sa.TEXT),
        sa.Column('type', sa.TEXT, nullable=False),
        sa.Column('subtype', sa.TEXT, nullable=False),
        sa.Column('extra_data', sa.TEXT),
        sa.Column('ignored', sa.INTEGER, nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['location'], ['location.location']),
        sa.UniqueConstraint('event_identifier', 'sequence_index')
    )
    
    op.create_table('evm_events_info',
        sa.Column('identifier', sa.INTEGER, primary_key=True),
        sa.Column('tx_hash', sa.BLOB, nullable=False),
        sa.Column('counterparty', sa.TEXT),
        sa.Column('product', sa.TEXT),
        sa.Column('address', sa.TEXT),
        sa.ForeignKeyConstraint(['identifier'], ['history_events.identifier'], ondelete='CASCADE', onupdate='CASCADE')
    )
    
    op.create_table('eth_staking_events_info',
        sa.Column('identifier', sa.INTEGER, primary_key=True),
        sa.Column('validator_index', sa.INTEGER, nullable=False),
        sa.Column('is_exit_or_blocknumber', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['identifier'], ['history_events.identifier'], ondelete='CASCADE', onupdate='CASCADE')
    )
    
    op.create_table('history_events_mappings',
        sa.Column('parent_identifier', sa.INTEGER, nullable=False),
        sa.Column('name', sa.TEXT, nullable=False),
        sa.Column('value', sa.INTEGER, nullable=False),
        sa.ForeignKeyConstraint(['parent_identifier'], ['history_events.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('parent_identifier', 'name', 'value')
    )
    
    op.create_table('skipped_external_events',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('data', sa.TEXT, nullable=False),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('extra_data', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location']),
        sa.UniqueConstraint('data', 'location')
    )
    
    # ETH2 staking
    op.create_table('eth2_validators',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('validator_index', sa.INTEGER, unique=True),
        sa.Column('public_key', sa.TEXT, nullable=False, unique=True),
        sa.Column('ownership_proportion', sa.TEXT, nullable=False),
        sa.Column('withdrawal_address', sa.TEXT),
        sa.Column('validator_type', sa.INTEGER, nullable=False),
        sa.Column('activation_timestamp', sa.INTEGER),
        sa.Column('withdrawable_timestamp', sa.INTEGER),
        sa.Column('exited_timestamp', sa.INTEGER),
        sa.CheckConstraint('validator_type IN (0, 1, 2)')
    )
    
    op.create_table('eth_validators_data_cache',
        sa.Column('id', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('validator_index', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('balance', sa.TEXT, nullable=False),
        sa.Column('withdrawals_pnl', sa.TEXT, nullable=False),
        sa.Column('exit_pnl', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['validator_index'], ['eth2_validators.validator_index'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.UniqueConstraint('validator_index', 'timestamp')
    )
    
    op.create_table('eth2_daily_staking_details',
        sa.Column('validator_index', sa.INTEGER, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('pnl', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['validator_index'], ['eth2_validators.validator_index'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.PrimaryKeyConstraint('validator_index', 'timestamp')
    )
    
    # ZKSync Lite
    op.create_table('zksynclite_transactions',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('tx_hash', sa.BLOB, nullable=False, unique=True),
        sa.Column('type', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('is_decoded', sa.INTEGER, nullable=False, server_default='0'),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('block_number', sa.INTEGER, nullable=False),
        sa.Column('from_address', sa.TEXT, nullable=False),
        sa.Column('to_address', sa.TEXT),
        sa.Column('asset', sa.TEXT, nullable=False),
        sa.Column('amount', sa.TEXT, nullable=False),
        sa.Column('fee', sa.TEXT),
        sa.ForeignKeyConstraint(['type'], ['zksynclite_tx_type.type']),
        sa.ForeignKeyConstraint(['asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.CheckConstraint('is_decoded IN (0, 1)')
    )
    
    op.create_table('zksynclite_swaps',
        sa.Column('tx_id', sa.INTEGER, nullable=False),
        sa.Column('from_asset', sa.TEXT, nullable=False),
        sa.Column('from_amount', sa.TEXT, nullable=False),
        sa.Column('to_asset', sa.TEXT, nullable=False),
        sa.Column('to_amount', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['tx_id'], ['zksynclite_transactions.identifier'], ondelete='CASCADE', onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['from_asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['to_asset'], ['assets.identifier'], onupdate='CASCADE')
    )
    
    # Other tables
    op.create_table('margin_positions',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('location', sa.CHAR(1), nullable=False, server_default='A'),
        sa.Column('open_time', sa.INTEGER),
        sa.Column('close_time', sa.INTEGER),
        sa.Column('profit_loss', sa.TEXT),
        sa.Column('pl_currency', sa.TEXT, nullable=False),
        sa.Column('fee', sa.TEXT),
        sa.Column('fee_currency', sa.TEXT),
        sa.Column('link', sa.TEXT),
        sa.Column('notes', sa.TEXT),
        sa.ForeignKeyConstraint(['location'], ['location.location']),
        sa.ForeignKeyConstraint(['pl_currency'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['fee_currency'], ['assets.identifier'], onupdate='CASCADE')
    )
    
    op.create_table('used_query_ranges',
        sa.Column('name', sa.VARCHAR(24), primary_key=True, nullable=False),
        sa.Column('start_ts', sa.INTEGER),
        sa.Column('end_ts', sa.INTEGER)
    )
    
    op.create_table('xpubs',
        sa.Column('xpub', sa.TEXT, nullable=False),
        sa.Column('derivation_path', sa.TEXT, nullable=False),
        sa.Column('label', sa.TEXT),
        sa.Column('blockchain', sa.TEXT, nullable=False),
        sa.PrimaryKeyConstraint('xpub', 'derivation_path', 'blockchain')
    )
    
    op.create_table('xpub_mappings',
        sa.Column('address', sa.TEXT, nullable=False),
        sa.Column('xpub', sa.TEXT, nullable=False),
        sa.Column('derivation_path', sa.TEXT, nullable=False),
        sa.Column('account_index', sa.INTEGER),
        sa.Column('derived_index', sa.INTEGER),
        sa.Column('blockchain', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['blockchain', 'address'], ['blockchain_accounts.blockchain', 'blockchain_accounts.account'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['xpub', 'derivation_path', 'blockchain'], ['xpubs.xpub', 'xpubs.derivation_path', 'xpubs.blockchain'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('address', 'xpub', 'derivation_path', 'blockchain')
    )
    
    op.create_table('nfts',
        sa.Column('identifier', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('name', sa.TEXT),
        sa.Column('last_price', sa.TEXT, nullable=False),
        sa.Column('last_price_asset', sa.TEXT, nullable=False),
        sa.Column('manual_price', sa.INTEGER, nullable=False, server_default='0'),
        sa.Column('owner_address', sa.TEXT),
        sa.Column('blockchain', sa.TEXT),
        sa.Column('is_lp', sa.INTEGER, nullable=False, server_default='0'),
        sa.Column('image_url', sa.TEXT),
        sa.Column('collection_name', sa.TEXT),
        sa.Column('usd_price', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['identifier'], ['assets.identifier'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['last_price_asset'], ['assets.identifier'], onupdate='CASCADE'),
        sa.CheckConstraint('manual_price IN (0, 1)'),
        sa.CheckConstraint('is_lp IN (0, 1)')
    )
    
    op.create_table('ens_mappings',
        sa.Column('address', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('ens_name', sa.TEXT),
        sa.Column('last_update', sa.INTEGER)
    )
    
    op.create_table('address_book',
        sa.Column('address', sa.TEXT, nullable=False),
        sa.Column('blockchain', sa.TEXT),
        sa.Column('name', sa.TEXT, nullable=False),
        sa.PrimaryKeyConstraint('address', 'blockchain')
    )
    
    op.create_table('rpc_nodes',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('name', sa.TEXT, nullable=False),
        sa.Column('endpoint', sa.TEXT, nullable=False),
        sa.Column('owned', sa.INTEGER, nullable=False, server_default='0'),
        sa.Column('active', sa.INTEGER, nullable=False, server_default='1'),
        sa.Column('weight', sa.TEXT, nullable=False, server_default='0.25'),
        sa.Column('blockchain', sa.TEXT, nullable=False),
        sa.CheckConstraint('owned IN (0, 1)'),
        sa.CheckConstraint('active IN (0, 1)')
    )
    
    op.create_table('user_notes',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('title', sa.TEXT, nullable=False),
        sa.Column('content', sa.TEXT, nullable=False),
        sa.Column('location', sa.TEXT, nullable=False),
        sa.Column('last_update_timestamp', sa.INTEGER, nullable=False),
        sa.Column('is_pinned', sa.INTEGER, nullable=False, server_default='0'),
        sa.CheckConstraint('is_pinned IN (0, 1)')
    )
    
    op.create_table('accounting_rules',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('type', sa.VARCHAR(256), nullable=False),
        sa.Column('subtype', sa.VARCHAR(256)),
        sa.Column('taxable', sa.INTEGER),
        sa.Column('count_entire_amount_spend', sa.INTEGER),
        sa.Column('count_cost_basis_pnl', sa.INTEGER),
        sa.Column('accounting_treatment', sa.VARCHAR(256)),
        sa.CheckConstraint('taxable IN (0, 1)'),
        sa.CheckConstraint('count_entire_amount_spend IN (0, 1)'),
        sa.CheckConstraint('count_cost_basis_pnl IN (0, 1)')
    )
    
    op.create_table('linked_rules_properties',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('accounting_rule', sa.INTEGER, nullable=False),
        sa.Column('property_name', sa.VARCHAR(256), nullable=False),
        sa.Column('setting_name', sa.TEXT, nullable=False),
        sa.Column('setting_value', sa.TEXT, nullable=False),
        sa.ForeignKeyConstraint(['accounting_rule'], ['accounting_rules.identifier'], ondelete='CASCADE'),
        sa.UniqueConstraint('accounting_rule', 'property_name')
    )
    
    op.create_table('unresolved_remote_conflicts',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('type', sa.INTEGER, nullable=False),
        sa.Column('asset', sa.TEXT, nullable=False),
        sa.Column('local_data', sa.TEXT, nullable=False),
        sa.Column('remote_data', sa.TEXT, nullable=False),
        sa.UniqueConstraint('type', 'asset')
    )
    
    op.create_table('key_value_cache',
        sa.Column('name', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('value', sa.TEXT, nullable=False)
    )
    
    op.create_table('calendar',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('name', sa.TEXT, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('description', sa.TEXT),
        sa.Column('counterparty', sa.TEXT),
        sa.Column('address', sa.TEXT),
        sa.Column('blockchain', sa.TEXT),
        sa.Column('color', sa.TEXT),
        sa.Column('auto_delete', sa.INTEGER, nullable=False, server_default='0'),
        sa.CheckConstraint('auto_delete IN (0, 1)')
    )
    
    op.create_table('calendar_reminders',
        sa.Column('identifier', sa.INTEGER, primary_key=True, nullable=False),
        sa.Column('event_id', sa.INTEGER, nullable=False),
        sa.Column('secs_before', sa.INTEGER, nullable=False),
        sa.Column('acknowledged', sa.INTEGER, nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['event_id'], ['calendar.identifier'], ondelete='CASCADE'),
        sa.CheckConstraint('acknowledged IN (0, 1)')
    )
    
    op.create_table('cowswap_orders',
        sa.Column('identifier', sa.TEXT, primary_key=True, nullable=False),
        sa.Column('tx_hash', sa.BLOB)
    )
    
    op.create_table('gnosispay_data',
        sa.Column('tx_hash', sa.BLOB, primary_key=True, nullable=False),
        sa.Column('timestamp', sa.INTEGER, nullable=False),
        sa.Column('merchant_name', sa.TEXT, nullable=False),
        sa.Column('merchant_city', sa.TEXT),
        sa.Column('country', sa.TEXT, nullable=False),
        sa.Column('mcc', sa.INTEGER, nullable=False),
        sa.Column('transaction_symbol', sa.TEXT, nullable=False),
        sa.Column('transaction_amount', sa.TEXT, nullable=False),
        sa.Column('billing_symbol', sa.TEXT),
        sa.Column('billing_amount', sa.TEXT),
        sa.Column('reversal_symbol', sa.TEXT),
        sa.Column('reversal_amount', sa.TEXT),
        sa.Column('reversal_tx_hash', sa.BLOB, unique=True)
    )
    
    # Create indexes
    op.create_index('idx_history_events_entry_type', 'history_events', ['entry_type'])
    op.create_index('idx_history_events_timestamp', 'history_events', ['timestamp'])
    op.create_index('idx_history_events_location', 'history_events', ['location'])
    op.create_index('idx_history_events_location_label', 'history_events', ['location_label'])
    op.create_index('idx_history_events_asset', 'history_events', ['asset'])
    op.create_index('idx_history_events_type', 'history_events', ['type'])
    op.create_index('idx_history_events_subtype', 'history_events', ['subtype'])
    op.create_index('idx_history_events_ignored', 'history_events', ['ignored'])


def downgrade() -> None:
    """Drop all tables"""
    # Drop indexes first
    op.drop_index('idx_history_events_ignored', 'history_events')
    op.drop_index('idx_history_events_subtype', 'history_events')
    op.drop_index('idx_history_events_type', 'history_events')
    op.drop_index('idx_history_events_asset', 'history_events')
    op.drop_index('idx_history_events_location_label', 'history_events')
    op.drop_index('idx_history_events_location', 'history_events')
    op.drop_index('idx_history_events_timestamp', 'history_events')
    op.drop_index('idx_history_events_entry_type', 'history_events')
    
    # Drop tables in reverse order of creation
    tables_to_drop = [
        'gnosispay_data', 'cowswap_orders', 'calendar_reminders', 'calendar',
        'key_value_cache', 'unresolved_remote_conflicts', 'linked_rules_properties',
        'accounting_rules', 'user_notes', 'rpc_nodes', 'address_book', 'ens_mappings',
        'nfts', 'xpub_mappings', 'xpubs', 'used_query_ranges', 'margin_positions',
        'zksynclite_swaps', 'zksynclite_transactions', 'eth2_daily_staking_details',
        'eth_validators_data_cache', 'eth2_validators', 'skipped_external_events',
        'history_events_mappings', 'eth_staking_events_info', 'evm_events_info',
        'history_events', 'evm_accounts_details', 'evm_transactions_authorizations',
        'optimism_transactions', 'evm_tx_mappings', 'evmtx_address_mappings',
        'evmtx_receipt_log_topics', 'evmtx_receipt_logs', 'evmtx_receipts',
        'evm_internal_transactions', 'evm_transactions', 'multisettings',
        'manually_tracked_balances', 'external_service_credentials',
        'user_credentials_mappings', 'user_credentials', 'timed_location_data',
        'timed_balances', 'tag_mappings', 'ignored_actions', 'blockchain_accounts',
        'tags', 'settings', 'assets', 'zksynclite_tx_type', 'balance_category', 'location'
    ]
    
    for table in tables_to_drop:
        op.drop_table(table)