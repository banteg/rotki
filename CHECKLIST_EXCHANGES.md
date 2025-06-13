## Detailed Checklist for Migrating `exchanges/` Package

### 1. Prepare Project

### 2. Drop Async Prefixes ✅

- [x] Rename `AsyncExchangeInterface` to `ExchangeInterface` and adjust imports.
- [x] Rename `AsyncExchangeWithExtras` → `ExchangeWithExtras`.
- [x] Rename `AsyncExchangeWithoutApiSecret` → `ExchangeWithoutApiSecret`.
- [x] Rename `AsyncExchangeManager` → `ExchangeManager`.
- [x] Rename any class names inside individual exchange modules (e.g., `AsyncKraken` → `Kraken`).
- [x] Update all references in routers, services, and tests.

### 3. Port Base Exchange Functionality ✅

- [x] Ensure `ExchangeInterface` uses `AsyncHTTPClient` for all network calls and handles rate limiting. Use the template in `rotki2/exchanges/base.py` as baseline.
- [x] Implement a common helper in `rotki2/exchanges/utils.py` for signing requests, pagination and error handling shared across exchanges.
- [x] Write unit tests for `ExchangeInterface` covering `first_connection`, `_apply_rate_limit`, and `close`.

### 4. Create Async Versions of All Exchanges 🔄 (In Progress)

- [x] For each file in `rotkehlchen/exchanges` (Binance, Bitstamp, Bitmex, etc.), create a counterpart in `rotki2/exchanges`.
  - [x] Kraken (fully implemented)
  - [x] Binance (fully implemented)
  - [x] Coinbase (fully implemented)
  - [x] Bitfinex (fully implemented)
  - [ ] Remaining exchanges (14 more to implement)
- [x] Convert all methods that perform I/O into `async def`.
- [x] Replace `requests` or `gevent` networking with `AsyncHTTPClient`.
- [x] Replace gevent primitives (`Semaphore`, `Event`, etc.) with `anyio.Lock`, `anyio.Event`.
- [x] Replace `gevent.sleep` calls and replace with `anyio.sleep`.
- [x] Keep method names consistent with v1 but without the `async_` prefix (e.g., `query_balances` not `async_query_balances`).
- [x] Implement exchange-specific rate limit logic using `_rate_limit_lock`.
- [x] Implement `get_extras` and `set_extras` for exchanges that require extra config (e.g., Kraken account type, Binance markets).
- [x] Write integration tests for each exchange against mocked HTTP responses.

### 5. Extend ExchangeManager ✅

- [x] Update `EXCHANGE_MAPPING` in `manager.py` to include all newly ported exchanges.
- [x] Ensure `setup_exchange`, `delete_exchange`, `edit_exchange` and other methods work with any exchange type.
- [ ] Add unit tests for manager operations (setup, edit, delete, close).

### 6. Update ExchangeService ✅

- [x] Refactor `ExchangeService` in `rotki2/api/v2/services/exchanges.py` to call the new async exchange classes.
- [x] Remove placeholder return values in `get_exchange_balances` and similar methods.
- [x] Implement error handling and proper translation to API responses.
- [ ] Cover the service with integration tests.

### 7. Adjust API Routers

- [ ] Ensure `rotki2/api/v2/routers/exchanges.py` invokes methods from `ExchangeService` correctly.
- [ ] Remove references to `SUPPORTED_EXCHANGES` from v1; rely on the manager's mapping.
- [ ] Update endpoints that still return dummy data or placeholders.

### 8. Database Integration

- [ ] Map any exchange-specific settings (e.g., Binance selected pairs) to SQLModel models in `rotki2/db/models/user`.
- [ ] Implement repository methods for saving/editing credentials and extras.
- [ ] Write migrations if new tables are needed for exchange data.

### 9. Remove Old Exchange Code

- [ ] Once all new modules are functional, delete unused `rotkehlchen/exchanges/*` modules except for data import helpers.
- [ ] Remove exchange-related logic from `rotkehlchen/rotkehlchen.py` and `rotkehlchen/api/rest.py`.

### 10. Testing and Validation

- [ ] Run unit tests for each exchange module.
- [ ] Run API integration tests under `rotki2/tests/api` to verify endpoints.
- [ ] Simulate a full workflow: add exchange credentials, query balances, fetch trade history, delete credentials.
- [ ] Validate that rate limiting works by simulating many quick requests.
- [ ] Confirm all tasks pass `ruff` and `mypy` checks.

### 11. Documentation and Cleanup

- [ ] Update `ARCHITECTURE.md` to describe the async exchange layer and remove references to gevent.
- [ ] Document each new exchange module with examples of expected API responses.
- [ ] Ensure docstrings include parameter types and return values.
- [ ] Remove temporary prints or debugging logs.

This checklist provides concrete, sequential actions to migrate the `exchanges/` package to the new async architecture, replacing the old gevent-based code with modern async code while keeping the project consistent and testable.
