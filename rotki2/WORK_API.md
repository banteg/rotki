Of course. It's crucial to have a clear, concise guide during a complex migration. This document will serve as a "North Star" for the developer, providing a clear map from the old codebase to the new one.

Here is the migration guide:

---

# **Rotki REST API Migration Guide: From v1 (Flask) to v2 (FastAPI)**

Hello! This guide is your single source of truth for the ongoing REST API migration. Its purpose is to help you quickly find where logic _used to be_, understand our new architecture, and know exactly where to place the _new_ logic.

## 1. The Big Picture: What Are We Doing?

We are migrating our API from an older, monolithic structure using **Flask** to a modern, layered architecture using **FastAPI**. At the same time, we are replacing our custom, synchronous database code with a clean, asynchronous **Repository Pattern** using **SQLModel**.

### **Why are we doing this?**

- **Maintainability:** Our new structure separates concerns (API routes, business logic, database queries), making the code easier to understand, debug, and extend.
- **Performance:** FastAPI and async database access are significantly faster and handle concurrent requests much more efficiently.
- **Developer Experience:** Type hints (with Pydantic & SQLModel) and automatic API documentation (with Swagger/OpenAPI) make development faster and less error-prone.

## 2. Our New v2 Architecture: The Three Layers

Our new API follows a standard three-layer architecture. **Think of it as a one-way street:** Routers talk to Services, and Services talk to Repositories. **Never break this flow.**

1.  **Routers (`/api/v2/routers/`)**

    - **What they do:** Define the API endpoints (`@router.get`, `@router.post`, etc.). They handle the raw HTTP request and response.
    - **Their only job:** Parse and validate incoming data (using Pydantic models) and call a single method in a **Service**. They should contain **zero business logic**.
    - **Where to find them:** `rotkehlchen/api/v2/routers/`

2.  **Services (`/api/v2/services/`)**

    - **What they do:** This is where all the **business logic** lives. They coordinate operations, process data, and make decisions.
    - **Their only job:** Fulfill the request from the Router by calling one or more **Repositories**. They orchestrate the work.
    - **Where to find them:** `rotkehlchen/api/v2/services/`

3.  **Repositories (`/api/v2/repositories/`)**
    - **What they do:** They are the **only** part of the application that directly interacts with the database.
    - **Their only job:** Execute database queries (SELECT, INSERT, UPDATE, DELETE) using **SQLModel** and return the data models. They know nothing about business rules.
    - **Where to find them:** `rotkehlchen/api/v2/repositories/`

## 3. The Migration Map: Finding Old Logic and Placing New Logic

This is your cheat sheet. Use it to find where the old code is and where its new, refactored version should go.

---

### **Topic: API Endpoints**

- **Where it was (v1):** `rotkehlchen/api/v1/resources.py`

  - Look for a class inheriting from `BaseMethodView`. The class name and methods (`get`, `post`, `put`, `patch`, `delete`) will tell you what the endpoint does.
  - **Example:** The `UsersResource` class handles requests to `/users`.

- **Where it goes now (v2):** `rotkehlchen/api/v2/routers/`

  - Find or create the relevant router file (e.g., `users.py` for user-related endpoints).
  - Create a new `async def` function decorated with `@router.get`, `@router.post`, etc.
  - This function should do **nothing but call a service**.
  - **Example:**

    ```python
    # in /api/v2/routers/users.py
    from rotkehlchen.api.v2.dependencies import get_user_service

    @router.get('/')
    async def get_users(
        service: Annotated[UserService, Depends(get_user_service)],
    ) -> UserListResponse:
        users = await service.get_all_users()
        return UserListResponse(users=users)
    ```

---

### **Topic: Business Logic**

- **Where it was (v1):** Mixed inside the `get`/`post` methods of the `MethodView` classes in `api/v1/resources.py`, and deep within the `Rotkehlchen` class (`rotkehlchen.py`).

  - This is the code that performs calculations, makes decisions, and calls multiple database or external API functions.

- **Where it goes now (v2):** `rotkehlchen/api/v2/services/`

  - Find or create a service that matches the business domain (e.g., `BalancesService`, `ReportsService`).
  - Create a new `async def` method in that service class.
  - This method should contain the core logic. It will take simple Python types (strings, ints) as arguments and call one or more **Repositories** to get data.
  - **Example:**

    ```python
    # in /api/v2/services/users.py
    from rotkehlchen.api.v2.repositories.user import UserRepository

    class UserService:
        def __init__(self, user_repo: UserRepository):
            self.user_repo = user_repo

        async def get_all_users(self) -> list[User]:
            db_users = await self.user_repo.get_all()
            # ... any processing or business logic on the users ...
            return [User.from_db_model(u) for u in db_users]
    ```

---

### **Topic: Database Queries & Operations**

- **Where it was (v1):** Everywhere, but primarily in `rotkehlchen/db/dbhandler.py` and its helper files like `db/history_events.py` and `db/accounting_rules.py`.

  - Look for methods that take a `cursor` object and execute raw SQL strings (`cursor.execute(...)`). These are the methods we need to replace.

- **Where it goes now (v2):** `rotkehlchen/api/v2/repositories/`

  - Find or create a repository for the specific database table you need to query (e.g., `HistoryRepository` for `history_events`).
  - Create a new `async def` method in the repository.
  - Inside this method, use **SQLModel's** `select()` statement to build your query in a Pythonic way.
  - This is the **ONLY** place database code should exist.
  - **Example:**

    ```python
    # in /api/v2/repositories/history.py
    from sqlmodel import select
    from rotkehlchen.db.models import HistoryEvent

    class HistoryRepository(BaseRepository[HistoryEvent]):
        async def find_by_location(self, location: str) -> list[HistoryEvent]:
            statement = select(HistoryEvent).where(HistoryEvent.location == location)
            async with self.db.read_ctx() as cursor:
                 # In a full async world, this would be:
                 # results = await self.session.exec(statement)
                 # For now, we wrap the old sync call:
                 results = await to_thread.run_sync(cursor.execute, statement)
                 return results.all()
    ```

### **Summary Table**

| Concern             | **Old Location (v1 - What to Replace)**                                          | **New Location (v2 - Where to Implement)**                                       |
| ------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **API Endpoints**   | `rotkehlchen/api/v1/resources.py` (MethodView classes)                           | `rotkehlchen/api/v2/routers/*.py` (async functions with `@router` decorators)    |
| **Business Logic**  | Inside `resources.py` methods, `rotkehlchen.py`, `data_handler.py`, etc.         | `rotkehlchen/api/v2/services/*.py` (async methods in service classes)            |
| **Database Access** | `rotkehlchen/db/dbhandler.py` and other files in `/db/` using `cursor.execute()` | `rotkehlchen/api/v2/repositories/*.py` (async methods using SQLModel `select()`) |
| **Database Models** | Schemas defined in `db/schema.py`                                                | `rotkehlchen/db/models/**/*.py` (classes inheriting from `SQLModel`)             |
| **Dependencies**    | Manual instantiation                                                             | `rotkehlchen/api/v2/dependencies.py` (using FastAPI's `Depends`)                 |

This document should serve as a practical guide. When you need to migrate a feature, follow the path: **V1 Resource -> V2 Router -> V2 Service -> V2 Repository**. Good luck
