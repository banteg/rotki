# RestAPI God Object Migration Analysis

## Overview
The RestAPI class in `/rotkehlchen/api/rest.py` contains 253 methods across ~5700 lines of code. This analysis categorizes these methods by functionality and maps them to their target v2 services.

## Method Categories and Target Services

### 1. **Assets Service** (41 methods)
Target: `/api/v2/services/assets.py`

#### Core Asset Management
- `query_list_of_all_assets()` - List all available assets
- `search_assets()` - Search assets by filter
- `search_assets_levenshtein()` - Fuzzy search for assets
- `get_asset_types()` - Get supported asset types
- `query_owned_assets()` - Get user's owned assets

#### Custom/User Assets
- `add_user_asset()` - Add custom user asset
- `edit_user_asset()` - Edit custom user asset
- `delete_asset()` - Delete custom asset
- `add_custom_asset()` - Add custom asset definition
- `edit_custom_asset()` - Edit custom asset definition
- `get_user_added_assets()` - Export user assets
- `import_user_assets()` - Import user assets

#### Asset Operations
- `replace_asset()` - Replace one asset with another
- `rebuild_assets_information()` - Rebuild asset cache
- `get_assets_mappings()` - Get asset identifier mappings
- `get_assets_updates()` - Check for asset updates
- `perform_assets_updates()` - Apply asset updates

#### Token Detection & Management
- `detect_evm_tokens()` - Detect EVM tokens for addresses
- `get_token_info()` - Get token information
- `fetch_token_balance_for_address()` - Fetch token balance

#### Spam/Ignored Assets
- `add_tokens_to_spam()` - Mark tokens as spam
- `remove_tokens_from_spam()` - Unmark spam tokens
- `add_to_spam_assets_false_positive()` - Mark false positives
- `get_spam_assets()` - Get spam asset list
- `add_ignored_assets()` - Add ignored assets
- `remove_ignored_assets()` - Remove ignored assets
- `get_ignored_assets()` - Get ignored assets list

#### Asset Icons
- `upload_asset_icon()` - Upload custom asset icon
- `refresh_asset_icon()` - Refresh asset icon
- `clear_icons_cache()` - Clear icon cache

### 2. **Balances Service** (21 methods)
Target: `/api/v2/services/balances.py`

#### Balance Queries
- `query_all_balances()` - Get all balances across platforms
- `query_netvalue_data()` - Get net value data
- `query_timed_balances_data()` - Get historical balance data
- `query_value_distribution_data()` - Get value distribution
- `get_historical_balance()` - Get balance at specific time

#### Manual Balance Tracking
- `get_manually_tracked_balances()` - Get manual balances
- `add_manually_tracked_balances()` - Add manual balance
- `edit_manually_tracked_balances()` - Edit manual balance
- `remove_manually_tracked_balances()` - Remove manual balance

#### Protocol-Specific Balances
- `get_amm_platform_balances()` - AMM balances
- `get_loopring_balances()` - Loopring L2 balances
- `get_dill_balance()` - Pickle Finance balances
- `get_nfts_balances()` - NFT balances

### 3. **Blockchain Service** (33 methods)
Target: `/api/v2/services/blockchain.py`

#### Account Management
- `get_blockchain_accounts()` - Get accounts by chain
- `add_single_blockchain_accounts()` - Add blockchain accounts
- `edit_single_blockchain_accounts()` - Edit account labels
- `remove_single_blockchain_accounts()` - Remove accounts
- `add_evm_accounts()` - Add EVM accounts with detection
- `refresh_evm_accounts()` - Refresh EVM account data

#### XPUB Management
- `add_xpub()` - Add Bitcoin XPUB
- `edit_xpub()` - Edit XPUB label
- `delete_xpub()` - Remove XPUB

#### RPC Node Management
- `get_rpc_nodes()` - Get configured RPC nodes
- `add_rpc_node()` - Add new RPC node
- `update_and_connect_rpc_node()` - Update RPC node
- `delete_rpc_node()` - Remove RPC node
- `connect_rpc_node()` - Test RPC connection

#### Transaction Management
- `refresh_transactions()` - Refresh transaction data
- `decode_evm_transactions()` - Decode EVM transactions
- `decode_pending_evmlike_transactions()` - Decode pending txs
- `get_count_transactions_not_decoded()` - Count undecoded txs
- `add_evm_transaction_by_hash()` - Add transaction by hash
- `delete_blockchain_transaction_data()` - Delete tx data

#### Chain Support
- `get_supported_chains()` - Get supported blockchains
- `query_blockchain_balances()` - Query chain balances

### 4. **Exchange Service** (12 methods)
Target: `/api/v2/services/exchanges.py`

#### Exchange Management
- `get_exchanges()` - List configured exchanges
- `setup_exchange()` - Add new exchange
- `edit_exchange()` - Edit exchange settings
- `remove_exchange()` - Remove exchange

#### Exchange Data
- `query_exchange_balances()` - Get exchange balances
- `query_exchange_history_events()` - Get exchange history
- `purge_exchange_data()` - Clear exchange data

#### Exchange-Specific
- `get_all_binance_pairs()` - Get Binance trading pairs
- `get_user_binance_pairs()` - Get user's Binance pairs
- `query_kraken_staking_events()` - Kraken staking data
- `get_binance_savings_history()` - Binance savings history
- `get_exchange_rates()` - Get exchange rates

### 5. **History Service** (19 methods)
Target: `/api/v2/services/history.py`

#### History Events Management
- `add_history_events()` - Add new events
- `edit_history_events()` - Edit existing events
- `delete_history_events()` - Delete events
- `get_history_events()` - Query history events
- `query_online_events()` - Query online sources

#### History Processing
- `process_history()` - Process accounting history
- `get_history_status()` - Get processing status
- `get_history_actionable_items()` - Get items needing action

#### History Export
- `export_history_events()` - Export to CSV
- `download_history_events_csv()` - Download CSV
- `export_processed_history_csv()` - Export processed data
- `download_processed_history_csv()` - Download processed

#### History Debug
- `get_history_debug()` - Export debug data
- `import_history_debug()` - Import debug data

### 6. **Auth Service** (19 methods)
Target: `/api/v2/services/auth.py`

#### User Management
- `get_users()` - List all users
- `create_new_user()` - Create new user
- `user_login()` - User login
- `user_logout()` - User logout
- `user_change_password()` - Change password

#### Premium Features
- `user_set_premium_credentials()` - Set premium key
- `user_premium_key_remove()` - Remove premium key
- `query_premium_components()` - Get premium features

#### User Data
- `get_user_notes()` - Get user notes
- `add_user_note()` - Add user note
- `edit_user_note()` - Edit user note
- `delete_user_note()` - Delete user note

#### User Database Snapshots
- `get_user_db_snapshot()` - Get DB snapshots
- `edit_user_db_snapshot()` - Edit snapshot
- `export_user_db_snapshot()` - Export snapshot
- `download_user_db_snapshot()` - Download snapshot
- `delete_user_db_snapshot()` - Delete snapshot
- `import_user_snapshot()` - Import snapshot

### 7. **Database Service** (6 methods)
Target: `/api/v2/services/database.py`

- `get_database_info()` - Database statistics
- `create_database_backup()` - Create backup
- `download_database_backup()` - Download backup
- `delete_database_backups()` - Delete backups
- `purge_module_data()` - Purge module data
- `purge_pnl_report_data()` - Purge report data

### 8. **Statistics Service** (3 methods)
Target: `/api/v2/services/statistics.py`

- `query_periodic_data()` - Get periodic stats
- `get_pnl_reports()` - Get PnL reports
- `get_report_data()` - Get report details

### 9. **Settings Service** (6 methods)
Target: `/api/v2/routers/settings.py`

- `get_settings()` - Get user settings
- `set_settings()` - Update settings
- `get_external_services()` - Get API keys
- `add_external_services()` - Add API keys
- `delete_external_services()` - Remove API keys

## Complex Methods Requiring Refactoring

### 1. **process_history()**
- **Current Issues**: 
  - Massive method (200+ lines)
  - Handles multiple responsibilities
  - Complex error handling
- **Refactoring Strategy**:
  - Split into: validation, processing, result formatting
  - Move to dedicated history processor class
  - Use event-driven architecture

### 2. **query_all_balances()**
- **Current Issues**:
  - Queries multiple sources synchronously
  - Complex aggregation logic
  - Poor error isolation
- **Refactoring Strategy**:
  - Use async/await for parallel queries
  - Separate balance sources into strategies
  - Implement circuit breaker pattern

### 3. **import_data()**
- **Current Issues**:
  - Handles multiple file formats
  - Complex validation logic
  - Database transaction management
- **Refactoring Strategy**:
  - Create importer classes per format
  - Use factory pattern
  - Implement proper rollback

### 4. **_eth_module_query()**
- **Current Issues**:
  - Generic method for multiple modules
  - Type safety issues
  - Poor error messages
- **Refactoring Strategy**:
  - Create specific methods per module
  - Use proper typing
  - Implement module-specific validators

## Dependencies to Address

### 1. **Circular Dependencies**
- RestAPI depends on Rotkehlchen instance
- Rotkehlchen depends on RestAPI for some operations
- **Solution**: Use dependency injection

### 2. **Global State**
- Direct database access throughout
- Shared greenlet pool
- **Solution**: Pass dependencies explicitly

### 3. **Mixed Concerns**
- Business logic in API layer
- Database queries in validators
- **Solution**: Proper layer separation

## Migration Priority

1. **High Priority** (Core functionality):
   - Auth Service
   - Assets Service
   - Balances Service
   - Settings Service

2. **Medium Priority** (Feature-complete):
   - Blockchain Service
   - Exchange Service
   - History Service

3. **Low Priority** (Can be gradual):
   - Statistics Service
   - Database Service
   - Protocol-specific endpoints

## Testing Strategy

1. **Unit Tests**: Test services in isolation
2. **Integration Tests**: Test service interactions
3. **API Tests**: Ensure endpoint compatibility
4. **Migration Tests**: Verify data integrity

## Notes

- Many methods have overlapping functionality that can be consolidated
- Several methods perform I/O in validators (anti-pattern)
- Async operations are handled with gevent (can use native async)
- Error handling is inconsistent across methods
- Response formatting is duplicated throughout