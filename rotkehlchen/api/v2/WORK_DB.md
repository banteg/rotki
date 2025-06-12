WORK_DB.md

Here is a comprehensive analysis of the database migration and a detailed, prioritized plan.

### **Migration Completeness Estimate (DB Layer): 50%**

This estimate is based on the significant progress in defining the new data models, but the considerable work remaining to transition the data access logic.

- **ORM Modeling (`db/models/`): 90% complete.** This is the most critical and impressive part of the migration so far. A tremendous amount of work has gone into defining the database schema using a modern ORM (SQLModel). This provides a solid, type-safe foundation for the new data access layer. The schemas are well-structured into `user/`, `globaldb/`, and `transient/` modules.
- **Repository Implementation (`api/v2/repositories/`): 20% complete.** While repository files exist, they are largely stubs. They correctly inherit from a `BaseRepository` but the custom query logic (e.g., `find_by_symbol`, `find_by_tx_hash`) is either placeholder, commented out, or incomplete. The real work of translating the old SQL queries into `SQLModel` queries has just begun.
- **Legacy DAO Refactoring (0% complete):** The existing data access logic is spread across `dbhandler.py` and numerous specialized files like `db/ens.py`, `db/history_events.py`, and `db/addressbook.py`. These files represent the "old way" and contain the logic that must be ported to the new v2 repositories.
- **Custom Query Logic (`filtering.py`): 0% complete.** This file contains a complex, custom-built system for creating dynamic SQL queries. While functional, it's a significant piece of technical debt. The v2 architecture correctly aims to replace this with more idiomatic ORM-based queries inside the repositories. This entire system needs to be migrated.
- **Database Upgrades (`upgrades/`): 50% complete (conceptually).** A robust versioned upgrade system is in place. However, it's built on raw SQL execution. The migration plan should consider how to handle future schema changes based on the new `SQLModel` definitions, potentially using a tool like Alembic while retaining the existing system for backward compatibility.

In essence, the blueprint for the new data layer is drawn (`db/models`), but the construction (implementing repositories and services to use them) is in its early stages.

---

### **Detailed Analysis of the Current State**

#### **Strengths:**

1.  **Modern ORM Foundation:** The decision to use SQLModel is excellent. It provides a single source of truth for schema, data validation, and ORM objects, which will drastically simplify the codebase.
2.  **Clear Repository Pattern:** The `api/v2/repositories/` structure is the correct pattern. It successfully decouples business logic (services) from data access logic (repositories).
3.  **Well-Defined Schema:** The raw SQL in `db/schema.py` and the migration scripts in `db/upgrades/` provide a crystal-clear source of truth for what the database schema _is_, making the task of verifying the `SQLModel` definitions much easier.

#### **Areas for Improvement & Gaps:**

1.  **The `DBHandler` God Object:** `db/dbhandler.py` is the v1 equivalent of the `RestAPI` God Object, but for the database. It mixes connection management with hundreds of data access methods for every domain (settings, assets, balances, etc.). This is the primary target for decomposition.
2.  **Logic in `filtering.py`:** This custom query-building framework is a major source of complexity. Each `DBFilterQuery` subclass is an abstraction that will be replaced by a more direct and readable `SQLModel` `select()` statement in a repository method.
3.  **Inconsistent Data Access:** The current codebase has multiple ways to access data: through `DBHandler`, through specialized classes like `DBEns`, and through direct cursor execution in some places. The migration must consolidate all of this into the new repository pattern.
4.  **SQLModel Completeness:** The models in `db/models/` need a thorough review to ensure all columns, relationships (`Relationship`), and constraints (`UniqueConstraint`, `ForeignKeyConstraint`) from the `db/schema.py` are correctly represented.

---

### **Migration Plan & Next Steps**

This plan focuses on systematically replacing the old data access layer with the new repository pattern, making the v2 API fully functional.

#### **Phase 1: Solidify the Repository Foundation (Immediate Priority)**

1.  **Finalize and Verify SQLModels:**

    - **Action:** Conduct a thorough, one-to-one review of the schemas in `db/schema.py` against the `SQLModel` classes in `db/models/`.
    - **Goal:** Ensure every column, type, constraint (PRIMARY KEY, FOREIGN KEY, UNIQUE), and relationship is perfectly mirrored. This is the bedrock of the entire v2 data layer; any mistakes here will cause problems later. Pay close attention to `ondelete='CASCADE'` rules.

2.  **Implement Core Repositories:**

    - **Action:** Begin porting the logic from the v1 DAO classes and `DBHandler` into the v2 repositories.
    - **Example 1 (`ENS`):**
      - Create `api/v2/repositories/ens.py` with an `ENSRepository` class.
      - Migrate the logic from `db/ens.py`'s `add_ens_mapping`, `get_reverse_ens`, etc., into methods within `ENSRepository`.
      - Replace raw SQL `INSERT`/`SELECT` with `SQLModel`'s `session.add()` and `session.exec(select(...))`.
    - **Example 2 (`History Events`):**
      - The `api/v2/repositories/history.py` file already exists.
      - Port the complex query logic from `db/history_events.py` (e.g., `get_history_events`, `get_history_events_count`) into methods within the `HistoryRepository`.
      - This is a good opportunity to simplify the queries using the ORM's relationship-following capabilities instead of manual `JOIN`s where possible.

3.  **Decommission `DBHandler` Methods:**
    - **Action:** As functionality is moved to a repository, mark the corresponding method in `DBHandler` as deprecated (`@deprecated` decorator or a `log.warning`).
    - **Goal:** Gradually shrink `DBHandler` until it is responsible only for connection management and running migrations.

#### **Phase 2: Replace Complex Querying and Upgrade Systems**

4.  **Refactor Filtering Logic:**

    - **Action:** For each v1 endpoint that uses a `DBFilterQuery` from `filtering.py`, identify the corresponding v2 service and repository.
    - **Goal:** Create repository methods that accept simple, type-hinted parameters (e.g., `from_ts: Timestamp`, `limit: int`, `asset_type: AssetType | None`) instead of a filter object. Inside the repository, build the `select()` statement dynamically based on these parameters.
    - **Example:** The logic in `DBHistoryEvents.get_history_events_and_limit_info` which takes a `HistoryBaseEntryFilterQuery` would be replaced by a `HistoryRepository.get_events` method with a signature like `def get_events(self, from_ts: ..., to_ts: ..., limit: ..., ...)`

5.  **Evolve the DB Upgrade Process:**
    - **Action (Short-term):** Continue using the existing `db/upgrades/` system for now, as it's required for users on older versions.
    - **Action (Long-term):** For any _new_ schema changes introduced for v2, use **Alembic**. Alembic integrates with SQLAlchemy/SQLModel and can auto-generate migration scripts based on changes to your `db/models/` classes. This is far more maintainable than writing raw SQL `ALTER TABLE` statements.

#### **Phase 3: Integration and Testing**

6.  **Full Service-Repository Integration:**

    - **Action:** Ensure all v2 services exclusively use their corresponding v2 repositories for all database interactions. Remove any lingering direct access to `DBHandler` or cursors from the service layer.
    - **Goal:** Enforce the clean architecture where services are completely unaware of the underlying database implementation details.

7.  **Write Repository and Service Tests:**
    - **Action:** For each repository, write unit tests using an in-memory SQLite database. These tests will verify that the `SQLModel` queries are correct and behave as expected.
    - **Action:** Write integration tests for the services, where the repositories are real but external dependencies (like exchange APIs) are mocked.

#### **Phase 4: Cleanup**

8.  **Deprecate and Remove:**
    - Once all logic has been migrated out of the v1 DAO classes (`ens.py`, `addressbook.py`, etc.) and `dbhandler.py`, they can be safely deleted.
    - `filtering.py` can be removed once all its filter classes have been replaced with repository methods.
    - `schema.py` and `minimized_schema.py` can be removed once the `SQLModel` classes in `db/models/` are the single source of truth and Alembic is used for migrations.
