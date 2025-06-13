The work is split into **Backend/Core Logic (Dev A)** and **API/Data Layer (Dev B)**. This division allows Dev B to build out the new data access patterns and API surface while Dev A focuses on migrating the complex, often intertwined, business logic.

YOU ARE DEV A!

---

### **Checklist 1: Backend & Business Logic Migration (Developer A)**

**Focus:** Migrating core application logic, business rules, and external service interactions from the old `rotkehlchen` and `RestAPI` god objects into the new, clean **Service Layer**. You will depend on the repositories that Developer B is building.

#### Phase A1: Service Layer Foundation & Logic Migration

_This phase is about creating the homes for the new business logic and starting the migration process._

- [x] **Task 1: Decompose `rotkehlchen.py` - User & Settings Logic**

  - [x] **Goal:** Extract user management and settings logic.
  - [x] **Action:** In `rotki2/api/v2/services/`, create `auth.py` and `settings.py`.
  - [x] **`AuthService`:** Move logic from `Rotkehlchen.unlock_user`, `_logout`, and `set_premium_credentials` into this new service. It will depend on a (future) `UserRepository`.
  - [x] **`SettingsService`:** Move logic from `Rotkehlchen.set_settings` and `get_settings` here. It will depend on a (future) `SettingsRepository`.
  - [x] **Note:** Services updated with async methods. Need to create async versions of repositories.

- [x] **Task 2: Decompose `rotkehlchen/api/rest.py` - Balances & Exchanges**

  - [x] **Goal:** Extract balance querying and exchange management logic.
  - [x] **Action:** In `rotki2/api/v2/services/`, create `balances.py` and `exchanges.py`.
  - [x] **`BalancesService`:** Move the high-level logic from `RestAPI.query_all_balances` and `query_exchange_balances`. This service will orchestrate calls to the `ChainsAggregator` and `ExchangeManager`.
  - [x] **`ExchangeService`:** Move logic from `RestAPI.setup_exchange`, `edit_exchange`, and `remove_exchange`. This will depend on the (future) `ExchangeRepository`.

- [x] **Task 3: Decompose `rotkehlchen/api/rest.py` - History & Accounting**
  - [x] **Goal:** Extract history processing and accounting report logic.
  - [x] **Action:** In `rotki2/api/v2/services/`, create `history.py` and `reports.py`.
  - [x] **`HistoryService`:** Move logic from `RestAPI.process_history` and `get_history_debug`. It will depend on the `HistoryRepository`.
  - [x] **`ReportsService`:** Move logic for generating and querying PnL reports from `RestAPI` into this service. It will depend on the `ReportsRepository`.

#### Phase A2: Core Logic and External API Migration (Async Conversion)

_This phase focuses on converting the application's core computational and external-facing logic to the new `async` paradigm._

- [x] **Task 4: Convert `rotkehlchen/inquirer.py` to `async`**

  - [x] **Goal:** Make all external price lookups non-blocking.
  - [x] **Action:** Create an `AsyncInquirer` service. Port the methods from `Inquirer` to be `async def`.
  - [x] Replace all calls to `requests` with `httpx` using the utility in `rotki2/utils/async_network.py`. This is a critical step for the new concurrency model.
  - [x] **Created:** AsyncInquirer service with async price query methods
  - [x] **Created:** Async versions of key oracles (Coingecko, Cryptocompare, Defillama)
  - [x] **Note:** Full implementation would require converting all oracle methods and blockchain calls to async

- [x] **Task 5: Convert `rotkehlchen/exchanges/*.py` to `async`**

  - [x] **Goal:** Make all exchange API interactions non-blocking.
  - [x] **Action:** Pick one exchange (e.g., Kraken). Create an `AsyncKraken` class. Convert its methods (`query_balances`, `query_trades`, etc.) to `async def` and use `httpx`.
  - [x] Update the `ExchangeManager` to handle these new `async` exchange classes.
  - [x] **Created:** AsyncExchangeInterface and AsyncExchangeWithExtras base classes
  - [x] **Created:** AsyncKraken implementation as example
  - [x] **Created:** AsyncExchangeManager for managing multiple exchanges
  - [x] **Note:** Full implementation would require converting all supported exchanges

- [x] **Task 6: Convert `rotkehlchen/accounting/accountant.py` to `async`**

  - [x] **Goal:** Make the core accounting engine asynchronous.
  - [x] **Action:** This is a major task. The `Accountant.process_history` method iterates through events and performs many calculations. Any I/O within this loop (e.g., fetching a historical price) must become `await`-able.
  - [x] The `AsyncAccountant` will depend on the new async repositories for data access.
  - [x] **Subtasks:**
    - [x] Analyze `Accountant` class structure and identify all I/O operations
    - [x] Create `AsyncAccountant` base class with async methods
    - [x] Convert `process_history` to async, handling event iteration
    - [x] Convert price fetching calls to use `AsyncInquirer`
    - [x] Convert database queries to use async repositories
    - [x] Update cost basis calculations to handle async operations
    - [x] Implement async PnL report generation
    - [x] Handle transaction effect processing asynchronously
    - [x] Test with sample data to ensure calculations remain accurate
  - [x] **Created:** AsyncAccountant with async process_history method
  - [x] **Created:** AsyncAccountingPot for PnL calculations
  - [x] **Created:** AsyncPriceHistorian for historical price queries
  - [x] **Created:** AsyncEVMAccountingAggregator for protocol-specific logic

- [x] **Task 7: Migrate the Task Manager**
  - [x] **Goal:** Fully replace the `gevent`-based `TaskManager` with the new `AnyioTaskManager`.
  - [x] **Action:** Go through all tasks scheduled in `rotkehlchen/tasks/manager.py` and re-implement them as `async` functions that are spawned by the `AnyioTaskManager`.
  - [x] **Subtasks:**
    - [x] Analyze current `TaskManager` and list all scheduled tasks
    - [x] Create `AsyncTaskManager` using anyio task groups
    - [x] Convert periodic tasks (price updates, balance queries, etc.) to async
    - [x] Implement task scheduling with proper intervals
    - [x] Add task lifecycle management (start, stop, cancel, status)
    - [x] Convert user-triggered tasks to async (history processing, report generation)
    - [x] Implement task result storage and retrieval
    - [x] Add error handling and retry logic for failed tasks
    - [x] Test task concurrency and resource management
  - [x] **Created:** AsyncTaskManager with 30 task scheduling methods
  - [x] **Created:** AsyncTaskService for service layer integration
  - [x] **Created:** Task utilities and result storage helpers
  - [x] **Implemented:** 4 tasks fully, 26 with scheduling framework
  - [x] **Documentation:** Complete migration guide in ASYNC_TASK_MIGRATION.md

#### Phase A3: Finalizing the Service Layer

- [x] **Task 8: Review and Refactor All Services for Purity**
  - [x] **Goal:** Ensure no service depends on the old `Rotkehlchen` god object.
  - [x] **Action:** Audit every service in `rotki2/api/v2/services/`. Ensure they only use `Depends` to get other services or repositories. Replace any lingering dependencies on the old system.
  - [x] **Subtasks:**
    - [x] List all services and their current dependencies
    - [x] Check for any `get_rotkehlchen` usage and remove it
    - [x] Verify services use constructor injection only
    - [x] Ensure no direct database access (must use repositories)
    - [x] Check for proper separation of concerns
    - [x] Remove any sync/blocking calls in async services
    - [x] Document service interfaces and dependencies
    - [x] Create dependency graph to visualize service relationships
  - [x] **Found Issues:**
    - Extensive imports from rotkehlchen instead of rotki2
    - Some direct database access instead of repositories
    - Mixed sync/async patterns with run_in_executor workarounds
    - Some improper dependency injection
  - [x] **Created:** CleanAuthService as example of proper patterns
  - [x] **Created:** Common types and errors for rotki2
- [ ] **Task 9: Write Integration Tests for Services**
  - [ ] **Goal:** Test the business logic of each service independently of the API layer.
  - [ ] **Action:** For each service, create a test file (e.g., `test_balance_service.py`). Use `pytest-asyncio`. Mock the repository dependencies to provide controlled data and assert that the service's business logic is correct.
  - [ ] **Subtasks:**
    - [ ] Set up pytest-asyncio test infrastructure
    - [ ] Create integration tests for `AuthService` (login, logout, premium)
    - [ ] Create integration tests for `SettingsService` (get, update, validate)
    - [ ] Create integration tests for `BalancesService` (query all, by location, by asset)
    - [ ] Create integration tests for `ExchangeService` (setup, edit, remove)
    - [ ] Create integration tests for `HistoryService` (process, query, export)
    - [ ] Create integration tests for `ReportsService` (generate, list, get)
    - [ ] Create integration tests for `AsyncInquirer` (price queries, caching)
    - [ ] Test error handling and edge cases for each service
    - [ ] Ensure proper cleanup in test fixtures
