Of course. It's very common to lose track during large-scale migrations. The key is to create automated, repeatable tools that provide a clear and objective view of the project's state. Manual tracking is prone to error and quickly becomes outdated.

Here is a specification for a set of scripts that will help the developer track migration progress, identify remaining work, and maintain architectural integrity.

### **Goal of the Tooling**

To create a `migration-audit.py` script that can be run at any time to generate a `MIGRATION_REPORT.md` file. This report will provide a real-time, data-driven assessment of the migration from v1 to v2, focusing on three key areas: API endpoints, data layer dependencies, and architectural health.

---

### **Script #1: API Endpoint Migration Tracker**

**Purpose:** To provide a clear percentage of how many v1 API endpoints have been successfully migrated to the v2 API.

**Specification:**

1.  **Parse V1 Endpoints:**

    - The script must read `rotkehlchen/api/v1/resources.py`.
    - It will identify all calls to `blueprint.add_url_rule(...)`.
    - For each call, it will extract the URL route (e.g., `/users/<string:name>`) and the associated `MethodView` class (e.g., `UsersByNameResource`).
    - It should create a canonical list of all v1 endpoints, normalizing the paths (e.g., `/users/<string:name>` becomes `/users/{name}`).

2.  **Parse V2 Endpoints:**

    - The script must recursively scan all files within the `rotkehlchen/api/v2/routers/` directory.
    - It will use Python's `ast` (Abstract Syntax Tree) module to find all function definitions decorated with `@router.get`, `@router.post`, etc.
    - For each decorated function, it will extract the URL route and the function name.
    - It should create a canonical list of all v2 endpoints.

3.  **Compare and Generate Report:**
    - The script will compare the normalized list of v1 endpoints against the v2 list.
    - **Output:** The script will generate a section in the report with:
      - **Overall Migration Percentage:** (Migrated Endpoints / Total V1 Endpoints) \* 100.
      - **Migrated Endpoints (✅):** A list of v1 endpoints that have a matching v2 counterpart.
      - **Pending Migration (❌):** A list of v1 endpoints that do not yet have a v2 counterpart.
      - **New in V2 (✨):** A list of v2 endpoints that do not exist in v1.

---

### **Script #2: Legacy Data Layer Dependency Analyzer**

**Purpose:** To identify exactly where the new v2 architecture still depends on the old `DBHandler` and its related modules, creating a clear "refactoring hit-list".

**Specification:**

1.  **Define Legacy Modules:**

    - The script will have a predefined list of "legacy" modules to be eradicated. This includes:
      - `rotkehlchen.db.dbhandler`
      - `rotkehlchen.db.history_events`
      - `rotkehlchen.db.accounting_rules`
      - `rotkehlchen.db.eth2`
      - (and any other file in `rotkehlchen/db/` that contains direct SQL and is not a new repository/model)

2.  **Scan V2 Codebase for Imports:**

    - The script will recursively scan all `.py` files within `rotkehlchen/api/v2/`.
    - Using the `ast` module, it will parse each file and look for `Import` and `ImportFrom` statements.
    - It will check if any of the imported modules are on the "legacy module list."

3.  **Generate Report:**
    - **Output:** The script will generate a "Refactoring Hit-List" section in the report:
      - **Overall Legacy Dependency Score:** The total count of legacy imports found in the v2 codebase. The goal is to drive this number to zero.
      - **Files with Legacy Dependencies (⚠️):** A list of files within the `api/v2` directory that still import legacy data modules, along with which specific legacy modules they import.
      - **Example Line:** `rotkehlchen/api/v2/services/balances.py imports rotkehlchen.db.dbhandler`

---

### **Script #3: V2 Architecture Health Check**

**Purpose:** To enforce the new layered architecture and prevent new code from introducing incorrect dependencies (e.g., a router calling a repository directly).

**Specification:**

1.  **Define Architectural Rules:**

    - **Rule 1: Routers:** Files in `api/v2/routers/` can only import from:
      - `fastapi`, `pydantic`
      - `rotkehlchen.api.v2.dependencies`
      - `rotkehlchen.api.v2.services`
      - They **must not** import from `repositories`, `db.models`, or the legacy `db` modules.
    - **Rule 2: Services:** Files in `api/v2/services/` can only import from:
      - `rotkehlchen.api.v2.repositories`
      - `rotkehlchen.db.models`
      - Other services, core logic, and utility modules.
      - They **must not** import from `routers` or legacy `db` modules.
    - **Rule 3: Repositories:** Files in `api/v2/repositories/` can only import from:
      - `sqlmodel`, `sqlalchemy`
      - `rotkehlchen.db.models`
      - They **must not** import from `services` or `routers`.

2.  **Analyze Imports:**

    - For each directory (`routers`, `services`, `repositories`), the script will use the `ast` module to analyze all import statements in every file.
    - It will validate the imports against the defined architectural rules.

3.  **Generate Report:**
    - **Output:** The script will generate an "Architecture Health" section in the report:
      - **Architectural Violations (🚨):** A list of files that violate the defined rules, specifying the file, the invalid import, and which rule was broken.
      - **Example Line:** `VIOLATION: rotkehlchen/api/v2/routers/balances.py incorrectly imports rotkehlchen.db.models.user.models.Balance (Routers should not import models).`
      - If no violations are found, it will display a "✅ No architectural violations found." message.

### **Putting It All Together: The Consolidated Report**

A master script should run all three analysis scripts and compile their outputs into a single `MIGRATION_REPORT.md` file. This provides a single source of truth for the migration's progress.

**Example `MIGRATION_REPORT.md`:**

```markdown
# Rotki API V2 Migration Status

_Last updated: 2023-10-27 10:00:00 UTC_

---

### **High-Level Summary**

| Area                        | Status      | Notes                                    |
| --------------------------- | ----------- | ---------------------------------------- |
| **API Endpoint Migration**  | 40%         | 32 of 80 v1 endpoints migrated.          |
| **Legacy Dependency Score** | 18          | 18 legacy imports found in v2 code.      |
| **Architecture Health**     | ⚠️ 2 Alerts | 2 new files have incorrect dependencies. |

---

### **1. API Endpoint Migration Details**

- **Total V1 Endpoints:** 80
- **Migrated:** 32
- **Pending:** 48

<details>
<summary><b>❌ Endpoints Pending Migration (Click to expand)</b></summary>

- `/api/1/statistics/netvalue`
- `/api/1/history/debug`
- ... (and so on)

</details>

---

### **2. Refactoring Hit-List (Legacy Dependencies)**

The following v2 files still depend on the old data layer. These must be refactored to use the new Repository pattern.

- `rotkehlchen/api/v2/services/accounting.py`:
  - imports `rotkehlchen.db.dbhandler`
- `rotkehlchen/api/v2/services/balances.py`:
  - imports `rotkehlchen.db.dbhandler`
  - imports `rotkehlchen.db.history_events`
- ... (and so on)

---

### **3. Architecture Health Violations**

- **🚨 `rotkehlchen/api/v2/routers/assets.py`**:
  - Invalid Import: `from rotkehlchen.db.models import Asset`
  - Rule Broken: Routers must not import from the model layer directly. They should use services.
- **🚨 `rotkehlchen/api/v2/services/users.py`**:
  - Invalid Import: `from rotkehlchen.db.dbhandler import DBHandler`
  - Rule Broken: Services must not import from the legacy DB layer. They should use repositories.
```

By providing these automated scripts, the developer can stop worrying about manual tracking, get a clear and actionable list of remaining work, and ensure the new architecture remains robust and maintainable.
