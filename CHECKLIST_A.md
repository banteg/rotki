### `Developer A: Core Infrastructure, API Foundation, and User/Asset Management`

This track focuses on setting up the fundamental application structure, authentication, database connections, and migrating the core User and Asset domains.

- **Phase 1: Core Setup & Database Foundation**

  - `[x]` **Finalize FastAPI App Setup:** In `rotki2/api/v2/app.py`, complete the `lifespan` manager to correctly initialize and shut down the `Rotkehlchen` instance and the new `AnyioTaskManager`.
  - `[x]` **Establish Async DB Connection:** In `rotki2/db/async_connection.py`, ensure `create_async_db_engine` and `create_async_session_factory` correctly handle the SQLCipher password and performance pragmas.
  - `[x]` **Implement Dependency Injection:** In `rotki2/api/v2/dependencies.py`, implement the `get_session` dependency to provide an `AsyncSession` to repositories.
  - `[x]` **Set up Alembic:** Run `alembic revision --autogenerate -m "Initial schema"` to create the first migration script based on all defined SQLModels. This script will be for new users. Do not apply it yet.
  - `[x]` **Refactor Task Manager:** In `rotki2/tasks/anyio_manager.py`, fully implement the task spawning and tracking logic. Migrate the scheduling logic from `rotkehlchen/tasks/manager.py` into `rotki2/tasks/async_manager.py`, replacing `gevent` calls with `anyio` equivalents.

- **Phase 2: Authentication & User Management**

  - `[x]` **Implement `UserRepository`:** In `rotki2/api/v2/repositories/user.py`, implement all methods for user and API key management, drawing logic from `rotkehlchen/db/dbhandler.py`.
  - `[x]` **Implement `AuthService`:** In `rotki2/api/v2/services/auth.py`, implement user authentication (`unlock_user`, `logout`), password changes, and API key management logic from `rotkehlchen/rotkehlchen.py` and `rotkehlchen/api/rest.py`.
  - `[x]` **Implement `auth.py` Router:** Wire up all endpoints in `rotki2/api/v2/routers/auth.py` to the `AuthService`.
  - `[x]` **Implement `users.py` Router:** Wire up all endpoints in `rotki2/api/v2/routers/users.py` to the `AuthService` and `UsersService`.
  - `[x]` **Implement `require_logged_in_user`:** In `rotki2/api/v2/dependencies.py`, implement a robust authentication check, likely using JWT tokens or a similar stateless mechanism, replacing the v1 session state check.

- **Phase 3: Settings & Info Management**

  - `[x]` **Implement `SettingsRepository`:** In `rotki2/api/v2/repositories/settings.py`, fully implement methods to get and set values in the `settings` and `multisettings` tables.
  - `[x]` **Implement `SettingsService`:** In `rotki2/api/v2/services/settings.py`, port the logic for validating and applying settings from `rotkehlchen/rotkehlchen.py` and `rotkehlchen/api/rest.py`.
  - `[x]` **Wire up `settings.py` Router:** Connect all endpoints in `rotki2/api/v2/routers/settings.py` to the `SettingsService`.
  - `[x]` **Wire up `info.py` Router:** Implement the logic for the info endpoint in `rotki2/api/v2/routers/info.py`.

- **Phase 4: Asset & Data Management**

  - `[ ]` **Finalize Asset Models:** Ensure all asset-related models in `rotki2/db/models/globaldb/assets.py` are complete and match the v1 schema.
  - `[ ]` **Implement `GlobalAssetRepository`:** In `rotki2/api/v2/repositories/globaldb_asset.py`, port all asset-related queries from `rotkehlchen/globaldb/handler.py`.
  - `[ ]` **Implement `AssetIgnoreRepository`:** In `rotki2/api/v2/repositories/asset_ignore.py`, implement the logic for managing ignored assets from `rotkehlchen/db/dbhandler.py`.
  - `[ ]` **Implement `AssetsService`:** In `rotki2/api/v2/services/assets.py`, consolidate asset management logic.
  - `[ ]` **Implement `DataService`:** In `rotki2/api/v2/services/data.py`, port data import/export logic from `rotkehlchen/data_import/manager.py`.
  - `[ ]` **Wire up `assets.py` Router:** Connect all endpoints to the `AssetsService`.
  - `[ ]` **Wire up `import_export.py` Router:** Connect endpoints to the `DataService`.

- **Phase 5: Cleanup & Verification**
  - `[ ]` **Remove Old User/Asset Files:** Delete `rotkehlchen/data_handler.py` and user/asset-related methods from `rotkehlchen.py` and `rotkehlchen/api/rest.py`.
  - `[ ]` **Write Integration Tests:** Create tests that cover the full user login -> settings change -> asset query flow.
