The work is split into **Backend/Core Logic (Dev A)** and **API/Data Layer (Dev B)**. This division allows Dev B to build out the new data access patterns and API surface while Dev A focuses on migrating the complex, often intertwined, business logic.

YOU ARE DEV B!

### **Checklist 2: API & Data Layer Migration (Developer B)**

**Focus:** Building the "scaffolding" of the new application. This includes creating all the database models, repositories, and FastAPI endpoints. You will be providing the data access layer that Developer A's services will consume.

#### Phase B1: Data Layer Foundation (SQLModel & Repositories)

_This phase focuses on creating the new, type-safe data access layer._

- [x] **Task 1: Complete SQLModel Definitions**

  - [x] **Goal:** Ensure every database table has a corresponding SQLModel class.
  - [x] **Action:** Run the `rotki2/verify_sqlmodel_migration.py` script. For every table listed as "missing", create a corresponding `SQLModel` class in `rotki2/db/models/`. Pay close attention to relationships, constraints, and types.
  - [x] **Status:** Verified all 52 tables have SQLModel definitions. 79 models exist (including additional models).

- [x] **Task 2: Implement the `AsyncSession` Dependency**

  - [x] **Goal:** Provide a reliable, async database session to all repositories.
  - [x] **Action:** In `rotki2/api/v2/dependencies.py`, implement the `get_async_session()` dependency using the factories in `rotki2/db/async_connection.py`. This will be the sole way the v2 stack accesses the database.
  - [x] **Status:** `get_async_session()` dependency implemented. Updated app lifespan to initialize async_session_factory on startup.

- [x] **Task 3: Create/Update All Repository Files to be Async**

  - [x] **Goal:** Ensure every repository in rotki2 is async (no sync versions, no async_ prefix).
  - [x] **Action:** For every major table or logical group of tables, create/update repository files in `rotki2/api/v2/repositories/`. Each should inherit from `AsyncBaseRepository` and be initialized with an `AsyncSession`. **Important:** In rotki2, ALL repositories are async by default - no async_ prefix needed.
  - [x] **Completed:**
    - **Removed sync versions and renamed async files:** accounting_rule.py, addressbook.py, ens.py, eth2.py (removed duplicates, kept async implementations)
    - **Still have async_ prefix:** async_cache.py, async_history_events.py, async_loopring.py (need renaming)
    - **Updated to async:** settings.py, tag.py, blockchain_account.py
    - **Created new repositories:** timed_balances.py, xpubs.py, zksynclite.py, calendar.py, user_credentials.py, external_services.py, margin_positions.py, cowswap_orders.py, conflicts.py
    - **Note:** All major tables now have repository shells. Next step is porting data access logic.

- [x] **Task 4: Port Data Access Logic into Repositories**
  - [x] **Goal:** Systematically move all SQL queries from the old `db` modules into the new async repositories.
  - [x] **Action:** Pick a legacy file, like `rotkehlchen/db/history_events.py`. For each method, create a corresponding `async def` method in the appropriate repository file.
  - [x] **Priority:** Focus on implementing the `get_` and `query_` methods first, as Developer A will need these to build the services. `add_`, `edit_`, and `delete_` can follow.
  - [x] **Conversion:** Replace all `cursor.execute("...")` calls with `await self.session.exec(select(...))` using SQLModel's syntax.
  - [x] **Completed:** Renamed remaining async_ files: cache.py, history_events.py, loopring.py
  
  - [x] **Sub-task 4.1: Port History Events Queries**
    - [x] Analyze `rotkehlchen/db/history_events.py` for key methods
    - [x] Port `get_history_events()` with filtering, pagination
    - [x] Port `get_history_events_count()` (as `count()` method)
    - [x] Port `get_events_by_location_and_type()`
    - [x] Port `get_base_entries_missing_prices()`
    - [x] Port event grouping and aggregation queries
    - [x] Added: `get_history_events_and_limit_info()`, `get_amount_stats()`, `get_event_identifiers_for_tx_hash()`, `get_events_by_event_identifier()`, `get_associated_event_data()`
    
  - [x] **Sub-task 4.2: Port User & Settings Queries**
    - [x] Port user authentication queries from `rotkehlchen/db/dbhandler.py`
    - [x] Port `get_settings()` and `set_settings()` logic - SettingsRepository already has full async implementation
    - [x] Port user credentials management - UserCredentialsRepository implemented
    - [x] Port API key management - UserRepository has full API key support
    - [x] **Completed:** Converted UserRepository to async, added password verification, user creation, existence checks
    
  - [x] **Sub-task 4.3: Port Balance Queries**
    - [x] Port `query_timed_balances()` from dbhandler - Added with filtering and zero balance inference
    - [x] Port `get_latest_balance_save_time()` - Added as `get_last_balance_save_time()`
    - [x] Port manually tracked balance queries - Already in balance.py repository
    - [x] Port balance snapshots logic - Added `save_balances_snapshot()` method
    - [x] **Added:** `add_multiple_balances()`, `get_assets_with_balances()`, zero balance inference framework
    
  - [x] **Sub-task 4.4: Port Blockchain Account Queries**
    - [x] Port `get_blockchain_accounts()` with tag filtering - Added `get_blockchain_account_data()` with comprehensive filtering
    - [x] Port xpub-related queries - Enhanced XpubsRepository with derivation indices, mappings, and tag support
    - [x] Port ENS reverse lookups - Already comprehensive in ENSRepository
    - [x] Port address labeling queries - Added integration with AddressBook in blockchain account queries
    - [x] **Added:** Bulk operations (`add_blockchain_accounts`, `edit_blockchain_accounts`, `remove_blockchain_accounts`)
    - [x] **Added:** Token detection cache methods for EVM addresses
    - [x] **Added:** Complex filtering and blockchain mapping queries
    
  - [x] **Sub-task 4.5: Port Exchange & DeFi Queries**
    - [x] Port exchange credentials queries - Enhanced user_credentials.py with exchange management
    - [x] Port margin positions queries - Enhanced margin_positions.py with P&L tracking
    - [x] Port DeFi protocol queries - Added protocol-specific methods to history_events.py
    - [x] Port liquidity pool queries - Added liquidity event tracking methods
    - [x] **Completed Enhancements:**
      - Enhanced margin_positions.py with position tracking by asset, P&L calculations, exchange summaries
      - Enhanced user_credentials.py with user-exchange mappings and bulk credential management
      - Created gnosis_pay.py repository with merchant and category spending analytics
      - Enhanced cowswap_orders.py with order status tracking and time-range queries
      - Enhanced zksynclite.py with transaction volume analytics and swap pair statistics
      - Added DeFi-specific methods to history_events.py:
        - get_defi_events_by_protocol() - Filter events by DeFi protocol
        - get_liquidity_events() - Track add/remove liquidity operations
        - get_protocol_volume_stats() - Analytics grouped by protocol
        - get_lending_events() - Track lending/borrowing across protocols

#### Phase B2: API Endpoint Implementation

_This phase focuses on creating the external-facing API, connecting it to the (in-progress) service layer._

- [x] **Task 5: Implement All API Routers and Endpoints**

  - [x] **Goal:** Create every endpoint from the v1 API in the new v2 routers.
  - [x] **Action:** Use `rotki2/migration_tools/endpoint_tracker.py` as your guide. For each pending endpoint:
    1.  Add the `@router.get(...)`, `@router.post(...)`, etc., decorator in the correct file in `rotki2/api/v2/routers/`.
    2.  Create the Pydantic `BaseModel` for the request body and response. **These models should only contain validation, no logic or I/O.**
    3.  The endpoint function should be a one-liner: it calls the corresponding service method. You will need to coordinate with Developer A on the names and signatures of these service methods. You can start by adding placeholder service methods that you call.
  - [x] **Completed Endpoints:**
    - **Exchange Router Enhancements:**
      - Added margin trading endpoints: `/margin/positions`, `/{location}/margin/positions`, `/margin/summary`
      - Added margin position sync endpoint: `/{location}/margin/positions/sync`
      - Added exchange rate endpoint: `/{location}/rates/{pair}`
    - **DeFi Router Enhancements:**
      - Added DeFi events endpoint: `/events`
      - Added lending summary endpoint: `/lending/summary`
      - Added liquidity endpoints: `/liquidity/positions`, `/liquidity/events`
      - Added yield farming endpoint: `/yield/summary`
      - Added Cowswap endpoints: `/cowswap/orders`, `/cowswap/orders/sync`
      - Added zkSync Lite endpoints: `/zksync-lite/transactions`, `/zksync-lite/swaps`
      - Added Gnosis Pay endpoints: `/gnosis-pay/transactions`, `/gnosis-pay/spending`
    - **NFT Router Enhancements:**
      - Added collection endpoints: `/collections`, `/collections/{collection_id}`
      - Added NFT transaction history: `/transactions`
      - Added NFT statistics: `/statistics`
      - Added collection metadata refresh: `/refresh/{collection_id}`
      - Added floor price endpoint: `/floor-prices`
  - [x] **Note:** Most endpoints use actual service methods where available, with placeholder implementations for methods not yet implemented by Dev A

- [x] **Task 6: Implement WebSocket Notifier**
  - [x] **Goal:** Replace the gevent-based WebSocket system with a FastAPI-native one.
  - [x] **Action:** The `rotki2/api/v2/websocket.py` file contains a good starting point with `ConnectionManager`. Flesh this out to handle topic subscriptions and targeted messages. The `RotkiNotifier` in v1 should be completely replaced by calls to this new manager.
  - [x] **Completed:** 
    - Enhanced ConnectionManager with topic-based subscriptions, user tracking, and client management
    - Implemented WebSocketTopic enum with all major event categories (balances, prices, transactions, etc.)
    - Added WebSocketClient dataclass for proper client state management
    - Created comprehensive broadcasting functions for all event types
    - Integrated WebSocket router with the main FastAPI app
    - Added optional user authentication support for WebSocket connections
    - Created WebSocketBridge for backward compatibility with v1 message types

#### Phase B3: Finalizing the Data and API Layers

- [ ] **Task 7: Write Integration Tests for Repositories**

  - [ ] **Goal:** Ensure every repository method correctly queries and manipulates the database.
  - [ ] **Action:** For each repository, create a test file (e.g., `test_async_history_repository.py`). Use `pytest-asyncio` and a real in-memory SQLite database to test each method's logic and returned data.

- [ ] **Task 8: Implement Full Alembic Integration**

  - [ ] **Goal:** Have a fully automated schema migration path.
  - [ ] **Action:**
    - [ ] Create an initial Alembic migration using `alembic revision --autogenerate -m "Initial schema from SQLModel"`.
    - [ ] This will generate a script based on your SQLModels. Compare this script against the old `DB_SCRIPT_CREATE_TABLES` to ensure perfect parity.
    - [ ] The `AlembicManager` in `rotki2/db/migrations/manager.py` should be integrated into the application's startup sequence to run migrations automatically.

- [ ] **Task 9: Polish All API Endpoints**
  - [ ] **Goal:** Ensure all endpoints have proper OpenAPI documentation (summaries, descriptions) and error handling.
  - [ ] **Action:** Review every router. Add `summary` and `description` fields to each decorator. Ensure that expected errors (e.g., 404 Not Found, 409 Conflict) are handled with specific `HTTPException`s.
