**Backend observations**

- The backend runs on Python 3.11 and exposes a Flask-based REST API with gevent for concurrency. This is visible in the dependency list with `gevent`, `flask`, `flask-cors` and related packages.
- Server startup patches Python’s standard library for gevent (`monkey.patch_all`) and launches a gevent `WSGIServer` that multiplexes Flask and websocket routes.
- Database access is handled via a custom SQLCipher wrapper (`pysqlcipher3`) and a custom gevent-aware driver (e.g., `gevent` patches around cursors).
- Concurrency and background tasks are implemented with explicit greenlets. Example: the task manager spawns gevent greenlets for scheduled operations and uses a gevent semaphore for locking.
- Websocket support is custom-built on top of `gevent-websocket` with a notifier that broadcasts serialized messages to connected clients.
- Extensive domain logic is encapsulated in the long `Rotkehlchen` class, which coordinates database operations, task scheduling, and external API calls.

**Current architectural challenges**

- Heavy reliance on gevent for concurrency complicates debugging and testing.
- The Flask + gevent server is largely synchronous and manually manages greenlets for tasks and websockets.
- Database access uses custom SQLCipher wrappers without an ORM, resulting in substantial boilerplate and direct SQL manipulation.
- The monolithic `Rotkehlchen` class couples many responsibilities (task management, API handlers, blockchain interactions, and more), making it hard to reason about and unit test.

**Suggested stack for a v2 rewrite**

1. **Python 3.11/3.12 with AnyIO**
   - Use `anyio` for concurrency instead of gevent, avoiding monkey-patching and enabling standard async tooling.
2. **FastAPI**
   - Provides a modern, async-ready API framework with automatic documentation and dependency injection.
   - Compatible with ASGI servers like Uvicorn for efficient websockets and HTTP handling.
3. **SQLAlchemy (with SQLCipher driver) and SQLModel**
   - Brings an ORM for models, schema management (with Alembic migrations), and optional async DB drivers.
   - Keeps encrypted SQLite (SQLCipher) support via the `pysqlcipher3` driver.
4. **Pydantic for validation**
   - Provides typed request/response models, replacing manual marshmallow schemas.
5. **Celery or RQ for background jobs**
   - Handles periodic tasks (balance updates, external API syncs) without manually spawning greenlets.
6. **Websockets via FastAPI**
   - Starlette’s built-in websocket support simplifies broadcast handling without custom gevent websockets.

**Proposed architectural improvements**

- **Layered structure**
  - **API Layer**: FastAPI routers for REST and websocket endpoints.
  - **Service Layer**: business logic grouped by domain (assets, exchanges, accounts, tasks).
  - **Repository/Data Layer**: SQLAlchemy models and repositories isolated from business logic.
- **Dependency injection**
  - Use FastAPI’s dependency system to inject services and database sessions, improving testability.
- **Task queue**
  - Offload periodic tasks and long-running computations to a background worker with Celery/RQ. Communicate results via database or websocket events.
- **Configuration & Environment**
  - Centralized settings module (possibly `pydantic-settings`) for environment-based configuration.
- **Modular packages**
  - Split large modules (like `rotkehlchen` and `tasks`) into dedicated packages (e.g., `rotki2.assets`, `rotki2.chains`, `rotki2.users`), each exposing clear interfaces.

This approach preserves Python’s ecosystem while modernizing the web stack, improving scalability and maintainability. The async stack (FastAPI + asyncio) simplifies concurrency and opens the door to efficient websockets and standardized background job processing. SQLAlchemy or SQLModel will reduce manual SQL management and facilitate migrations, while a layered architecture isolates concerns and enables unit tests on individual services.