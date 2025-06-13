## The Great Rotki Refactor: A Detailed Checklist

This checklist will guide you step-by-step through the migration from the `rotkehlchen` (v1) architecture to the `rotki2` (v2) architecture. Each step is designed to be a small, manageable piece of work. Follow them in order to ensure a clean and successful refactor.

### Phase 0: Setup and Housekeeping

_This phase is about setting up our tools and environment to make the rest of the migration smooth and safe._

- [ ] **Understand the Goal:** Read and understand the core architectural goals:

  - [ ] **From Flask to FastAPI:** We want modern, fast, async-native API endpoints.
  - [ ] **From raw SQL to SQLModel:** We want type-safe, maintainable database queries instead of writing SQL strings by hand.
  - [ ] **From Gevent to Anyio:** We want explicit `async`/`await` for I/O operations, not hidden magic.
  - [ ] **From God Objects to Services:** We want to break down huge files into small, focused, and testable components.

- [ ] **Set up a Linter Rule:** Create a custom lint rule (e.g., for Pylint or Flake8) that forbids importing `get_rotkehlchen` from `rotki2/api/v2/dependencies.py` inside any other v2 service. This will programmatically prevent the god object anti-pattern from spreading.

### Phase 1: Severing Ties - Enforcing the New Architecture

_This is the most critical phase. We must isolate the new v2 system from the old v1 system to avoid creating a messy hybrid. These steps are non-negotiable for a clean refactor._

- [ ] **Eliminate `get_rotkehlchen` Dependency:**

  - [ ] **Identify:** Find every file in `rotki2/api/v2/` that uses `Depends(get_rotkehlchen)`.
  - [ ] **Why:** This is a "service locator" anti-pattern. It gives a service access to the _entire_ old application, defeating the purpose of creating small, focused services. It makes testing and reasoning about the code impossible.
  - [ ] **Action:** For each usage, determine the specific dependency the service _actually_ needs (e.g., `DatabaseService`, `SettingsService`). Refactor the endpoint to use `Depends(get_new_service)` instead. If a service doesn't exist, you must create it.
  - [ ] **Goal:** The `get_rotkehlchen` dependency should be completely removed from the v2 API.

- [ ] **Establish the V2 Async Database Connection:**

  - [ ] **Identify:** The `get_db_connection` dependency in `rotki2/api/v2/dependencies.py` returns the old, `gevent`-based `DBConnection`. This is a major source of potential bugs.
  - [ ] **Why:** The new async code must use a new async database connection. Mixing `gevent` and `anyio` event loops via the database driver will lead to deadlocks and hard-to-debug failures.
  - [ ] **Action:**
    - [ ] In `rotki2/api/v2/dependencies.py`, create a new dependency `get_async_session() -> AsyncGenerator[AsyncSession, None]` that uses the `create_async_session_factory` and `create_async_db_engine` from `rotki2/db/async_connection.py`.
    - [ ] All **v2 repositories** (e.g., `AsyncENSRepository`) must be changed to accept an `AsyncSession` in their constructor, not a `DBConnection`.
    - [ ] All repository methods must be `async` and use `await self.session.exec(...)`.
  - [ ] **Goal:** No file inside `rotki2/` should import from `rotkehlchen.db.drivers.gevent`.

- [ ] **Unify Repository and Test Patterns:**
  - [ ] **Identify:** There are both synchronous (`test_ens_repository.py`) and asynchronous (`test_async_ens_repository.py`) versions of repositories and tests.
  - [ ] **Why:** This creates confusion and doubles the maintenance work. The target is a pure async stack.
  - [ ] **Action:** Delete all synchronous repositories and their tests from the `rotki2/` directory. All data access logic must be implemented in the `async` repositories.

### Phase 2: The Data Layer Migration (Repositories)

_This is the methodical work of moving all database logic from the old `db` modules into the new `async` repositories, using SQLModel._

- [ ] **Migrate `rotkehlchen/db/ens.py`:**

  - [ ] Ensure all methods from the old `DBEns` class have an `async` equivalent in `rotki2/api/v2/repositories/async_ens.py`.
  - [ ] Replace all raw SQL strings with `sqlmodel.select()` queries.
  - [ ] Verify the logic in `update_values` is correctly ported.

- [ ] **Migrate `rotkehlchen/db/addressbook.py`:**

  - [ ] Ensure all methods from the old `DBAddressbook` class have an `async` equivalent in `rotki2/api/v2/repositories/async_addressbook.py`.
  - [ ] Pay close attention to the `read_ctx` and `write_ctx` logic. This should now be handled by the `AsyncSession` from the dependency injector.
  - [ ] Convert the dynamic filter query logic to use SQLAlchemy's selectable system if possible, or keep it as `text()` but ensure it's executed with `await session.execute()`.

- [ ] **Migrate `rotkehlchen/db/loopring.py`:**

  - [ ] Ensure all methods from the old `DBLoopring` class have an `async` equivalent in `rotki2/api/v2/repositories/async_loopring.py`. This one is simpler as it queries the `multisettings` table.

- [ ] **Migrate `rotkehlchen/db/accounting_rules.py`:**

  - [ ] Ensure all methods from the old `DBAccountingRules` class have an `async` equivalent in `rotki2/api/v2/repositories/async_accounting_rule.py`.
  - [ ] Convert the logic for adding, updating, and querying rules to use `SQLModel`. The complex filtering in `query_rules` will require careful porting.

- [ ] **Decompose and Migrate `rotkehlchen/db/dbhandler.py`:**

  - [ ] **Why:** This is the largest god object. It cannot be migrated 1-to-1. It must be broken down.
  - [ ] **Action:** Go through `DBHandler` method by method. For each method, decide which new repository it belongs to and implement it there.
  - [ ] **Checklist for `dbhandler.py` methods:**
    - [ ] `get_setting`, `set_setting` -> `SettingsRepository`
    - [ ] `add_external_service_credentials`, `get_all_external_service_credentials` -> `ExternalServicesRepository`
    - [ ] `add_to_ignored_assets`, `get_ignored_asset_ids` -> `AssetIgnoreRepository`
    - [ ] `add_multiple_balances`, `save_balances_data` -> `BalanceRepository`
    - [ ] `add_exchange`, `edit_exchange`, `get_exchange_credentials` -> `ExchangeRepository` (needs creation)
    - [ ] `add_margin_positions`, `get_margin_positions` -> `TradingRepository` (needs creation)
    - [ ] `add_bitcoin_xpub`, `delete_bitcoin_xpub` -> `XpubRepository` (needs creation)
    - [ ] ... and so on for all ~200 methods in the file.

- [ ] **Migrate Remaining `db` Modules:**
  - [ ] **`rotkehlchen/db/history_events.py`** -> `rotki2/api/v2/repositories/async_history_events.py`
  - [ ] **`rotkehlchen/db/evmtx.py`** -> `rotki2/api/v2/repositories/evm_transaction.py`
  - [ ] **`rotkehlchen/db/eth2.py`** -> `rotki2/api/v2/repositories/async_eth2.py`
  - [ ] ... and so on for every file in `rotkehlchen/db/`.

### Phase 3: The Business Logic Migration (Services)

_With a solid data layer, we can now move the core application logic into the new services._

- [ ] **Decompose `rotkehlchen/api/rest.py`:**

  - [ ] Go through each method in the `RestAPI` class.
  - [ ] For a method like `query_exchange_balances`, create a corresponding `async def get_exchange_balances(...)` method in `rotki2/api/v2/services/balances.py`.
  - [ ] The new service method should call the appropriate repository methods (e.g., `exchange_repository.get_all()`) and perform the business logic (querying the exchange APIs, processing data).
  - [ ] Ensure all network calls within services use `httpx` via your `async_network.py` utility.

- [ ] **Decompose `rotkehlchen/rotkehlchen.py`:**
  - [ ] This is the other major god object. Its logic needs to be carefully distributed.
  - [ ] **Example:** The `unlock_user` logic belongs in `AuthService`. The `set_premium_credentials` logic belongs in `PremiumService`. The `query_balances` orchestrator logic belongs in `BalancesService`.
  - [ ] This is a complex task. For each piece of logic, ask: "What is the single responsibility of this code?" and move it to the service that matches that responsibility.

### Phase 4: The API Endpoint Migration

_Now we connect the external world to our new, clean business logic._

- [ ] **Implement Endpoints Systematically:**
  - [ ] Run `python rotki2/migration_tools/endpoint_tracker.py` to find an endpoint marked as pending.
  - [ ] In the appropriate v2 router file (e.g., `rotki2/api/v2/routers/balances.py`), create the FastAPI route (`@router.get(...)`).
  - [ ] Define the Pydantic `BaseModel` for the request body and the response. This replaces the old `marshmallow` schemas. **Do not put any I/O or business logic in these models.**
  - [ ] The endpoint function itself should be very simple:
    1.  Accept the request model and any dependencies (`Depends(...)`).
    2.  Call one method on the corresponding service.
    3.  Return the result from the service.
  - [ ] Add a test for the new endpoint in `rotki2/tests/api/`.

### Phase 5: Concurrency and Performance Polish

_This phase ensures the application is truly non-blocking and performant._

- [ ] **Audit for Blocking Calls:**

  - [ ] Manually review or use a static analysis tool to find any synchronous I/O calls within `async def` functions in the `rotki2` directory. This includes `requests.get`, standard `open()`, `time.sleep()`, etc.
  - [ ] Replace them with their `anyio` or `httpx` equivalents (e.g., `await anyio.sleep()`).

- [ ] **Remove `pytestgeventwrapper.py`:**
  - [ ] Once all v1 code paths are gone, the test suite should no longer require `gevent`.
  - [ ] The goal is to run tests with a standard `pytest-asyncio` setup.

### Phase 6: Finalization - Erasing the Past

_The refactor is not done until the old code is gone._

- [ ] **Deprecate V1 Endpoints:** As v2 endpoints become stable, add logging to the corresponding v1 Flask endpoints to warn that they will be removed in a future version.
- [ ] **Switch Over All Clients:** Ensure the frontend and any other API clients are exclusively using the v2 endpoints.
- [ ] **Remove V1 API Code:** Delete the entire `rotkehlchen/api` directory.
- [ ] **Remove V1 DB Code:** Delete the entire `rotkehlchen/db` directory (except for `rotkehlchen/db/models/` if you decide to keep it for some reason, though it should ideally be moved).
- [ ] **Remove `rotkehlchen/rotkehlchen.py`:** The final act. Once all its logic is moved to services, this file can be deleted. The new application entry point will be `rotki2/api/v2/app.py`.
- [ ] **Update All Documentation:** Go through all project documentation and update it to reflect the new architecture, new API endpoints, and new testing procedures.
- [ ] **Celebrate!** You've completed a massive and highly valuable technical refactor.
