### Refactoring and Modernization Checklist

#### **Phase 0: Project Setup & Foundational Tooling**

- [x] **Dependency Management:** Add the necessary libraries for the new architecture.

  - [x] Add `aiosqlite` to your project's dependencies (`pyproject.toml` or `requirements.txt`). This will be the async driver for SQLite.
  - [x] Add `anyio` to your project's dependencies. This will be used for managing async tasks and concurrency, replacing `gevent`.
  - [x] Add `SQLModel` as a dependency if it's not already explicitly there (it might be a sub-dependency of FastAPI).

- [x] **Async Database Configuration:** Set up the core components for async database access.

  - [x] Create a new module (e.g., `rotkehlchen/db/async_connection.py`) to manage the async database engine and session creation.
  - [x] In this new module, define a function to create an `anyio`-compatible `AsyncEngine` from `sqlalchemy.ext.asyncio`. Configure it to use `aiosqlite` and to connect to the user's encrypted database file.
  - [x] Implement an `async_sessionmaker` to create `AsyncSession` instances.
  - [x] Create a FastAPI dependency (e.g., in `api/v2/dependencies.py`) called `get_async_session` that yields an `AsyncSession` for each request. This will be the standard way endpoints get a database session.

- [x] **Base Repository:** Establish a reusable pattern for data access.
  - [x] Create a `BaseRepository` class in `api/v2/repositories/base.py`.
  - [x] This base class should accept an `AsyncSession` in its constructor.
  - [x] Implement generic, `async` CRUD methods in the base class: `get()`, `get_all()`, `create()`, `update()`, `delete()`.

#### **Phase 1: Standardize the Data Access Layer (DAL) - The Core Migration**

This is the most critical and extensive phase. The goal is to replace all direct database interactions through `DBHandler` and raw SQL with the new async Repository pattern using SQLModel. **Repeat these steps for each data model/domain.**

##### **Pattern: Migrating a Single DB Module (Example: `db/ens.py`)**

- [x] **Step 1: Identify the Target Module.**

  - [x] Select `db/ens.py` as the first module to migrate.

- [x] **Step 2: Create the SQLModel.**

  - [x] In `db/models/user/ens.py`, define the `ENSMapping` class using `SQLModel`.
  - [x] Ensure the model fields match the table schema, using appropriate types like `str`, `int`, and `Column` for constraints.

- [x] **Step 3: Create the Async Repository.**

  - [x] Create a new file: `api/v2/repositories/ens.py`.
  - [x] Inside, define `ENSRepository(BaseRepository[ENSMapping])`.
  - [x] Its `__init__` should accept an `AsyncSession`.

- [x] **Step 4: Implement Repository Methods.**

  - [x] For _every function_ in the old `db/ens.py`, create a corresponding `async def` method in `ENSRepository`.
  - [x] **Example Migration (`add_ens_mapping`):**
    - [x] The old method uses raw SQL: `INSERT INTO ens_mappings ... ON CONFLICT ...`.
    - [x] The new `async def add_ens_mapping` method will use the session:
      ```python
      existing_mapping = await session.get(ENSMapping, address)
      if existing_mapping:
          existing_mapping.ens_name = name
          existing_mapping.last_update = now
      else:
          existing_mapping = ENSMapping(...)
      session.add(existing_mapping)
      await session.commit()
      ```
  - [x] **Example Migration (`get_reverse_ens`):**
    - [x] The old method uses raw SQL: `SELECT ... FROM ens_mappings WHERE address IN (...)`.
    - [x] The new `async def get_reverse_ens` method will use a SQLModel `select`:
      ```python
      statement = select(ENSMapping).where(ENSMapping.address.in_(addresses))
      results = await session.exec(statement)
      # Process results into the required dictionary format
      ```

- [x] **Step 5: Create a Service Layer.**

  - [x] Create a new file: `api/v2/services/ens.py`.
  - [x] Define `ENSService`.
  - [x] The service's `__init__` will take `ENSRepository` as a dependency.
  - [x] Move any business logic from the original `db/ens.py` (like the logic in `update_values`) into methods within `ENSService`. These service methods will call the repository methods.

- [x] **Step 6: Update the API Endpoint.**

  - [x] Locate the FastAPI endpoint(s) in `api/v2/routers/` that handle ENS lookups (e.g., in `api/v2/routers/names.py`).
  - [x] Change the endpoint function to be `async def`.
  - [x] Use FastAPI's `Depends` to inject the `ENSService`.
  - [x] Replace the old call (e.g., `rotkehlchen.data.db.ens.get_reverse_ens(...)`) with a call to the new service (e.g., `await ens_service.get_reverse_lookup(...)`).

- [x] **Step 7: Test the New Implementation.**

  - [x] Write unit tests for the `ENSRepository`, mocking the `AsyncSession`.
  - [x] Write unit tests for the `ENSService`, mocking the `ENSRepository`.
  - [x] Write integration tests for the new FastAPI endpoint to ensure it works end-to-end. Use the old tests for `db/ens.py` as a reference for expected behavior.

- [ ] **Step 8: Repeat for All Other DB Modules.**
  - [x] Repeat the process for `db/addressbook.py` -> `AddressbookRepository`.
  - [x] Repeat the process for `db/loopring.py` -> `LoopringRepository`.
  - [x] Repeat the process for `db/accounting_rules.py` -> `AccountingRuleRepository`.
  - [x] Repeat the process for `db/history_events.py` -> `HistoryEventsRepository`.
  - [x] Repeat the process for `db/eth2.py` -> `Eth2Repository` (validators, daily stats, performance).
  - [ ] Repeat the process for `db/cache.py` -> `CacheRepository` (key-value cache, dynamic cache).
  - [ ] Repeat the process for `db/settings.py` -> `SettingsRepository` (user settings management).
  - [ ] Repeat the process for `db/evmtx.py` -> `EvmTransactionsRepository` (EVM transaction storage).
  - [ ] Repeat the process for `db/queried_addresses.py` -> `QueriedAddressesRepository`.
  - [ ] Repeat the process for `db/ranges.py` -> `RangesRepository` (query ranges tracking).
  - [ ] Repeat the process for `db/calendar.py` -> `CalendarRepository` (calendar events, reminders).
  - [ ] Repeat the process for `db/custom_assets.py` -> `CustomAssetsRepository`.
  - [ ] Repeat the process for `db/reports.py` -> `ReportsRepository` (accounting reports).
  - [ ] Repeat the process for `db/snapshots.py` -> `SnapshotsRepository` (balance snapshots).
  - [ ] Repeat the process for `db/l2withl1feestx.py` -> `L2WithL1FeesRepository`.
  - [ ] Repeat the process for `db/arbitrum_one_tx.py` -> `ArbitrumOneRepository`.
  - [ ] Repeat the process for `db/unresolved_conflicts.py` -> `UnresolvedConflictsRepository`.
  - [ ] **DBHandler Decomposition:** The final goal is to make `DBHandler` obsolete.
  
- [x] **Step 9: Fix Raw SQL Usage in Migrated Modules.**
  - [x] Fix `async_history_events.py` - Extensive raw SQL usage with complex multi-table joins for history events operations (documented why raw SQL is kept).
  - [x] Fix `async_eth2.py` - Complex ETH2 validator and staking queries with JOINs and UNIONs for statistical data (converted simple queries to ORM, documented complex ones).
  - [x] Fix `async_accounting_rule.py` - Custom filter queries with raw SQL bindings for rule management (fixed to use ORM where possible).
  - [x] Fix `async_addressbook.py` - Custom filter queries for address book entries with pagination (fixed to use ORM where possible).
  - [x] Fix `asset_ignore.py` - Minor issues with model references causing fallback to raw SQL (fixed typos in model references).

#### **Phase 2: Eradicate `gevent` and Embrace `anyio`**

This can be done in parallel with Phase 1, but its full benefits are realized once the DAL migration is complete.

- [x] **Task Management:** Replace the `gevent`-based task manager.

  - [x] Analyze `greenlets/manager.py`. Its purpose is to spawn background tasks.
  - [x] Create a new task manager, `tasks/anyio_manager.py`, that uses an `anyio` task group (`anyio.create_task_group()`) to run background tasks.
  - [x] The new manager should provide similar functionality: starting tasks, tracking them, and retrieving results.

- [x] **Concurrency Primitives:** Replace `gevent` locks.

  - [x] Search the codebase for `gevent.lock.Semaphore`.
  - [x] Replace each instance with an `anyio.Semaphore`. Note that `anyio` locks must be used within an `async` context (`async with lock:`).

- [x] **Network Calls:** Refactor blocking network calls.

  - [x] Identify all places that use the synchronous `requests` library.
  - [x] Replace them with an async HTTP client like `httpx`.
  - [x] This is critical in modules under `exchanges/`, `externalapis/`, and `oracles/`.

- [x] **Entry Point:** Switch the web server to run in a standard `asyncio` context.
  - [x] Modify `api/v2/run.py` to use a standard `uvicorn` worker instead of a `gevent` worker. The `anyio` backend will handle the event loop.

#### **Phase 3: Decompose God Objects (`Rotkehlchen` and `DBHandler`)**

As you migrate the DAL in Phase 1, you will naturally start this process.

- [ ] **`DBHandler` Decomposition:**

  - [ ] For every method in `DBHandler`, ensure its functionality is fully moved into one or more `Repository` classes.
  - [ ] For example, `get_manually_tracked_balances` should be in a `ManualBalanceRepository`. `add_exchange` should be part of an `ExchangeCredentialsRepository`.
  - [ ] The ultimate goal is to delete `db/dbhandler.py`. Mark it as complete only when no part of the codebase imports it.

- [ ] **`Rotkehlchen` Class Decomposition:**

  - [ ] Analyze the public methods of `rotkehlchen/rotkehlchen.py`.
  - [ ] Group methods by domain/feature (e.g., `process_history`, `query_balances`, `add_exchange`).
  - [ ] For each group, create a corresponding `Service` class in `api/v2/services/`.
  - [ ] Move the business logic from `rotkehlchen.py` into the new service.
  - [ ] Refactor the service to take its dependencies (Repositories, other services) in its constructor. It should **not** have a reference to the main `rotkehlchen` object.
  - [ ] Update the corresponding FastAPI endpoint in `api/v2/routers/` to depend on the new service.

- [ ] **`DataHandler` Decomposition:**
  - [ ] The `DataHandler` class is another potential god object. Apply the same decomposition process: identify responsibilities, create services, and refactor callers.

#### **Phase 4: Finalize the API and Deprecate v1**

- [ ] **Endpoint Parity Check:**

  - [ ] Create a spreadsheet or document listing every single v1 API endpoint from `api/v1/resources.py`.
  - [ ] For each v1 endpoint, map it to its new v2 equivalent in `api/v2/routers/`.
  - [ ] Identify any v1 endpoints that have not been migrated and prioritize their implementation in v2.

- [ ] **Update API Clients:**

  - [ ] Ensure the frontend application (or any other API client) is updated to use only the v2 endpoints.

- [ ] **Remove v1 API Code (Eventually):**
  - [ ] Once you have confirmed no clients are using the v1 API, you can proceed with deletion.
  - [ ] Mark the entire `api/v1/` directory for deletion.
  - [ ] Mark `api/server.py` for deletion.

#### **Phase 5: Final Review and Cleanup**

- [ ] **Code Review:** Perform a full-codebase search for any remaining `gevent` imports or usages and remove them.
- [ ] **Dependency Review:** Check `pyproject.toml` and remove `gevent` and `greenlet`.
- [ ] **Configuration Cleanup:** Remove any configuration options that were specific to the old Flask/gevent setup.
- [ ] **Final Testing:** Run the entire test suite to ensure no regressions were introduced during the final cleanup phase.
- [ ] **Documentation:** Update any developer documentation, architecture diagrams, or READMEs to reflect the new `FastAPI` + `SQLModel` + `anyio` architecture.
