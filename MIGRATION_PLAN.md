Below is a high‑level technical assessment of the main architectural issues you are likely to face when you replace **Flask + raw SQL** with **FastAPI + SQLModel** in this code‑base.  All points are drawn from the structure and patterns visible in the uploaded `api/` package.&#x20;

---

### 1.  HTTP Layer:  Flask → FastAPI

| Current pattern                                                                                                                 | Impact when moving                                                                                     | Why it matters / what to do                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Class‑based views (`BaseMethodView` ➜ `flask.views.MethodView`)**<br>Endpoints defined as subclasses with `post/get` methods. | FastAPI favours function routes; there is no 1‑to‑1 MethodView analogue.                               | • Flatten each view class into one or more `@router.post/get` functions.<br>• Inject `rest_api` (the service layer) via [FastAPI `Depends`](https://fastapi.tiangolo.com/tutorial/dependencies/) instead of holding it on `self`.                                  |
| **`webargs.flaskparser.use_kwargs` decorators** (plus a custom `ResourceReadingParser`)                                         | FastAPI uses Pydantic models for input validation; the decorator approach disappears.                  | • Rewrite Marshmallow/Webargs schemas as Pydantic models where practical.<br>• For code paths that rely on `schema.post_load()` side‑effects (e.g. building `FilterQuery` objects), move that logic to helper functions the route calls after Pydantic validation. |
| **Custom request parsing that passes the *resource object* into Marshmallow**                                                   | In FastAPI you can inject the *same* extra context object through dependencies.                        | • Replace the `resource_object` argument with a dependency that yields the service / db handle needed for validation.                                                                                                                                              |
| **Flask error handlers / return type `flask.Response`**                                                                         | FastAPI expects either `dict`/`PydanticModel` or `Response` from `starlette.responses`.                | • Centralise exception mapping by writing a small set of `exception_handlers` wired into the FastAPI app.                                                                                                                                                          |
| **Blueprint registration & URL prefixes**                                                                                       | Use FastAPI `APIRouter` instances with prefixes and tags; mount them where blueprints were registered. |                                                                                                                                                                                                                                                                    |

---

### 2.  Validation & Serialization:  Marshmallow → Pydantic

* **Marshmallow schemas dominate the project** (hundreds of lines of custom `Field` subclasses).  Direct 1‑for‑1 conversion is expensive, but keeping Marshmallow inside FastAPI will negate many FastAPI perks (automated docs, speed).
* **Recommendation**

  1. **Green‑field Pydantic models** only for the public request/response surfaces you refactor first.
  2. Keep internally‑used Marshmallow pieces for now; call them from route logic (you can `await run_in_threadpool(schema.load, data)` if they are CPU‑heavy).
  3. Gradually retire Marshmallow fields by moving domain‑specific coercion into *value objects* reused by both SQLModel and Pydantic (e.g. `ChecksumEvmAddress`, `Asset`).

---

### 3.  Concurrency model

* **Flask is synchronous.** Many endpoints spawn background “async tasks” manually via the `async_query` flag.
* **FastAPI gives you real `async def`** plus `BackgroundTask` helpers.
* **Action items**

  * Audit every call that touches the DB, external RPCs or network I/O.
  * Make service‑layer calls `async` and use an *async SQLAlchemy engine* under SQLModel (supported since SQLModel 0.0.14).
  * Ensure any long‑running CPU‑bound work is pushed to a worker queue (Celery, RQ, dramatiq) rather than an `async` endpoint to avoid blocking the event loop.

---

### 4.  WebSockets

* You already have `api/websockets/notifier.py` built on Flask‑SSE or `flask-socketio` (not shown, but inferred).
* FastAPI’s WebSocket implementation is Starlette‑native; the API surface differs (no Flask request context). Plan for a full rewrite of notifier registration & broadcast logic.

---

### 5.  Data Layer:  Raw SQL → SQLModel

| Pain point in current code                                                                             | How SQLModel changes it                                                                                                                                                                | Migration strategy                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Literal SQL everywhere** – e.g. validation that queries `cursor.execute('SELECT …')` inside schemas. | SQLModel is an *ORM* layer producing SQLAlchemy Core/ORM queries. You will want to push such logic out of validation and into repository/service classes that speak SQLModel sessions. | 1. Identify “read‑only” queries that can stay in raw SQL for now (performance‑critical joins etc.).<br>2. Define SQLModel models for core tables and migrate the simple CRUD paths first.<br>3. For highly‑parametric filter builders (e.g. `HistoryEventFilterQuery.make`), keep generating SQLAlchemy Core expressions – SQLModel exposes `model.__table__` for this. |
| **No central session scope.**  Code opens cursors directly.                                            | FastAPI likes one session per request using dependency‑injected context managers.                                                                                                      | Provide a dependency `get_session()` that yields a SQLModel `Session` (sync) or `AsyncSession` and add it to each route.                                                                                                                                                                                                                                                |
| **Hand‑rolled migrations.**                                                                            | Leverage Alembic autogeneration once models exist.                                                                                                                                     | Autogenerate once per release; freeze the raw‑SQL migration scripts for previous versions.                                                                                                                                                                                                                                                                              |

---

### 6.  Enumerations, Custom Types, HexBytes, etc.

* These are already PEP‑compliant classes, so you can reuse them in Pydantic by registering [validators / `json_encoders`](https://docs.pydantic.dev/latest/usage/exporting_models/#custom-json-encoders).
* For SQLModel you may need SQLAlchemy \[TypeDecorator] wrappers (e.g. `ChecksumEvmAddressType`) to map to `VARCHAR`.

---

### 7.  Testing & Tooling

* **Pytest fixtures that spin up a Flask test client** will become FastAPI `TestClient`.
* **OpenAPI docs** are autogenerated by FastAPI; invest time in describing response models so the new docs remain as detailed as today’s Marshmallow schema docs.

---

### 8.  Incremental Migration Game‑plan

1. **Dual‑run phase**

   * Wrap the existing Flask app with Starlette’s `WSGIMiddleware` and mount it under `/legacy/*` inside the new FastAPI app.
   * Gradually port endpoints to FastAPI `/v2/*` paths; deprecate `/legacy/*` when stable.

2. **Data‑layer bridge**

   * Introduce SQLModel side‑by‑side with the raw‑SQL helpers.
   * Give every SQLModel model a `.from_row(row)` helper so old code can consume ORM objects without refactoring all callers.

3. **Validation bridge**

   * Write shim functions that convert Pydantic request models ➜ dict ➜ Marshmallow schema for endpoints not yet migrated.

4. **Full switch**

   * Delete WSGIMiddleware, stop importing Flask, drop Marshmallow once all endpoints & services use Pydantic/SQLModel.

---

### 9.  Common Pitfalls to Avoid

* **Synchronous DB driver on async engine** – use `asyncpg` for Postgres or `aiosqlite` for SQLite.
* **Blocking crypto/hash utilities inside `async def`** – run them in a thread pool.
* **Large response objects built with `json.dumps`** – let FastAPI stream them or use BackgroundTasks.
* **Global singletons (e.g. `EthereumInquirer`)** – make them implicit dependencies so you don’t share a non‑thread‑safe client across tasks.

---

## Bottom line

Moving to FastAPI + SQLModel will give you type‑checked request models, automatic OpenAPI docs, first‑class async I/O, and an ORM that integrates with those models.  The **biggest architectural lift** is unbundling the tight Flask‑Webargs‑Marshmallow coupling that currently pervades every layer – start there, isolate the domain/business logic into plain services, and the HTTP & DB stacks can be swapped out with far less friction.&#x20;
