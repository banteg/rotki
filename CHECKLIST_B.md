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

- [ ] **Task 4: Port Data Access Logic into Repositories**
  - [ ] **Goal:** Systematically move all SQL queries from the old `db` modules into the new async repositories.
  - [ ] **Action:** Pick a legacy file, like `rotkehlchen/db/history_events.py`. For each method, create a corresponding `async def` method in the appropriate repository file.
  - [ ] **Priority:** Focus on implementing the `get_` and `query_` methods first, as Developer A will need these to build the services. `add_`, `edit_`, and `delete_` can follow.
  - [ ] **Conversion:** Replace all `cursor.execute("...")` calls with `await self.session.exec(select(...))` using SQLModel's syntax.
  - [ ] **Status:**
    - [ ] Rename remaining async_ files: async_cache.py → cache.py, async_history_events.py → history_events.py, async_loopring.py → loopring.py
    - [ ] Port get_/query_ methods from rotkehlchen/db/history_events.py
    - [ ] Port get_/query_ methods from rotkehlchen/db/dbhandler.py
    - [ ] Port balance-related queries
    - [ ] Port user/settings queries

#### Phase B2: API Endpoint Implementation

_This phase focuses on creating the external-facing API, connecting it to the (in-progress) service layer._

- [ ] **Task 5: Implement All API Routers and Endpoints**

  - [ ] **Goal:** Create every endpoint from the v1 API in the new v2 routers.
  - [ ] **Action:** Use `rotki2/migration_tools/endpoint_tracker.py` as your guide. For each pending endpoint:
    1.  Add the `@router.get(...)`, `@router.post(...)`, etc., decorator in the correct file in `rotki2/api/v2/routers/`.
    2.  Create the Pydantic `BaseModel` for the request body and response. **These models should only contain validation, no logic or I/O.**
    3.  The endpoint function should be a one-liner: it calls the corresponding service method. You will need to coordinate with Developer A on the names and signatures of these service methods. You can start by adding placeholder service methods that you call.

- [ ] **Task 6: Implement WebSocket Notifier**
  - [ ] **Goal:** Replace the gevent-based WebSocket system with a FastAPI-native one.
  - [ ] **Action:** The `rotki2/api/v2/websocket.py` file contains a good starting point with `ConnectionManager`. Flesh this out to handle topic subscriptions and targeted messages. The `RotkiNotifier` in v1 should be completely replaced by calls to this new manager.

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
