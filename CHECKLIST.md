### **Goal:** Port the v1 accounting engine to the new v2 async architecture.

This involves migrating the logic from `rotkehlchen/accounting/` to `rotki2/accounting/`, converting synchronous code to async/await, and replacing direct database access with the new repository pattern.

---

### **Phase 0: Setup and Renaming**

This phase ensures your environment is ready and conforms to the new codebase standards.

- [x] **Rename async classes:** In the `rotki2/` directory, rename all classes that have an `Async` prefix to remove it, as the entire new codebase is asynchronous by default.
  - [x] Rename `rotki2/accounting/accountant.py` -> `Accountant`.
  - [x] Rename `rotki2/accounting/pot.py` -> `AccountingPot`.
  - [x] Rename `rotki2/accounting/aggregator.py` -> `EVMAccountingAggregator`.
  - [x] Rename `rotki2/accounting/price_historian.py` -> `PriceHistorian`.
  - [x] Search for and rename any other `Async` prefixed classes in the `rotki2/` tree.
- [x] **Familiarize yourself:** Thoroughly read through the v1 files in `rotkehlchen/accounting/` to understand the data flow and logic. Pay close attention to `accountant.py`, `pot.py`, and `cost_basis/base.py`.

---

### **Phase 1: Porting Foundational Data Structures**

Before we can port the logic, we need the data structures that the logic operates on. These are mostly data containers and can be ported with minimal changes, aside from updating imports.

- [x] **Port `PNL` and `PnlTotals`:**
  - [x] Create the file `rotki2/accounting/pnl.py`.
  - [x] Copy the `PNL` and `PnlTotals` classes from `rotkehlchen/accounting/pnl.py` into the new file.
  - [x] Update any internal type hints to reflect the new structure.
- [x] **Port `AccountingEventMixin` and `AccountingEventType`:**
  - [x] Create the file `rotki2/accounting/mixins.py`.
  - [x] Copy the `AccountingEventMixin` and `AccountingEventType` from `rotkehlchen/accounting/mixins/event.py`.
- [x] **Port `ProcessedAccountingEvent`:**
  - [x] Create `rotki2/accounting/structures.py` for shared data structures.
  - [x] Move `ProcessedAccountingEvent` from `rotkehlchen/accounting/structures/processed_event.py` to `rotki2/accounting/structures.py`.
  - [x] Update its imports to use the newly ported `PNL` and other v2 types.
  - [x] The `to_exported_dict` method's `database` argument should be changed to a repository or service dependency in the future, but for now, you can leave it and we will refactor it later.
- [x] **Port Cost Basis Data Structures:**
  - [x] Create `rotki2/accounting/cost_basis/structures.py`.
  - [x] Move `AssetAcquisitionEvent`, `AssetSpendEvent`, `MatchedAcquisition`, and `CostBasisInfo` classes from `rotkehlchen/accounting/cost_basis/base.py` into the new file.
  - [x] Update imports within these classes to point to v2 structures like `ProcessedAccountingEvent`.

---

### **Phase 2: Porting the Core Cost Basis Logic**

This is the most critical calculation logic. We will port it class by class, ensuring each part is async and uses the new patterns.

- [x] **Create the `CostBasisCalculator` base:**
  - [x] Create the file `rotki2/accounting/cost_basis/calculator.py`.
  - [x] Copy the `BaseCostBasisMethod` class into this new file.
- [x] **Port FIFO method:**
  - [x] Copy the `FIFOCostBasisMethod` class from `rotkehlchen/accounting/cost_basis/base.py` to `rotki2/accounting/cost_basis/calculator.py`.
- [x] **Port LIFO method:**
  - [x] Copy the `LIFOCostBasisMethod` class to `rotki2/accounting/cost_basis/calculator.py`.
- [x] **Port HIFO method:**
  - [x] Copy the `HIFOCostBasisMethod` class to `rotki2/accounting/cost_basis/calculator.py`.
- [x] **Port Average Cost Basis (ACB) method:**
  - [x] Copy the `AverageCostBasisMethod` class to `rotki2/accounting/cost_basis/calculator.py`.
  - [x] This method has complex logic; ensure all its helper methods are also ported.
- [x] **Port `CostBasisCalculator` orchestrator:**
  - [x] Copy the `CostBasisCalculator` class from `rotkehlchen/accounting/cost_basis/base.py` to `rotki2/accounting/cost_basis/calculator.py`.
  - [x] Refactor its `__init__` to accept a `DatabaseService` or specific repositories instead of the old `DBHandler`.
  - [x] Convert `reduce_asset_amount` and `spend_asset` to `async` methods, as they may implicitly trigger price lookups in the future.
- [x] **Port Pre-fork Logic:**
  - [x] Create `rotki2/accounting/cost_basis/prefork.py`.
  - [x] Copy `handle_prefork_asset_acquisitions` and `handle_prefork_asset_spends` from `rotkehlchen/accounting/cost_basis/prefork.py`.
  - [x] Ensure these functions call the new `CostBasisCalculator` methods.

---

### **Phase 3: Porting the `AccountingPot`**

The `AccountingPot` holds the state for an accounting run. It uses the `CostBasisCalculator` and needs to be fully asynchronous.

- [ ] **Refactor `rotki2/accounting/pot.py`:**
  - [ ] Update the `__init__` method:
    - Replace `DBHandler` with `DatabaseService`.
    - Replace `EVMAccountingAggregators` with the new `EVMAccountingAggregator` from `rotki2`.
    - Replace the synchronous `PriceHistorian` with the new `PriceHistorian` from `rotki2/accounting/price_historian.py`.
  - [ ] **Convert methods to `async`:**
    - [ ] Convert `get_rate_in_profit_currency` to `async def` and change the `PriceHistorian.query_historical_price` call to `await self.price_historian.query_historical_price(...)`.
    - [ ] Convert `add_in_event` to `async def`. It calls `get_rate_in_profit_currency`, so it needs to `await` it.
    - [ ] Convert `add_out_event` to `async def`. It also calls `get_rate_in_profit_currency`.
    - [ ] Convert `add_asset_change_event` to `async def`.
    - [ ] Convert `get_prices_for_swap` to `async def` and `await` its internal calls to `get_rate_in_profit_currency`.
  - [ ] **Update Database Interactions:**
    - [ ] The `_add_processed_event` method calls `DBAccountingReports`. This dependency needs to be updated to use the `ReportsRepository` from `rotki2`. The call will look something like `await self.reports_repo.add_report_data(...)`.

---

### **Phase 4: Porting the `Accountant`**

The `Accountant` orchestrates the entire process.

- [ ] **Refactor `rotki2/accounting/accountant.py`:**
  - [ ] Update the `__init__` method:
    - Replace dependencies with their v2 counterparts (`DatabaseService`, `ChainsAggregator`, etc.).
    - Ensure it initializes the new `AccountingPot`.
  - [ ] **Port `process_history` method:**
    - [ ] Change the method signature to `async def process_history(...)`.
    - [ ] The main loop `while True:` should remain, but the call to `_process_event` inside it must be awaited: `await self._process_event(...)`.
    - [ ] Replace `gevent.sleep()` with `await anyio.sleep()`.
    - [ ] Database interactions for creating and updating the report must now use the `ReportsRepository`.
  - [ ] **Port `_process_event` method:**
    - [ ] Change the method signature to `async def _process_event(...)`.
    - [ ] The call to `event.process()` will now be `await event.process(...)`. This is a crucial change that will ripple through all event classes.
  - [ ] **Port `export` method:**
    - [ ] This method depends on `CSVExporter`. You need to port `rotkehlchen/accounting/export/csv.py` to `rotki2/accounting/export/csv.py` first. Ensure its methods are `async` if they perform I/O.

---

### **Phase 5: Porting Supporting Modules and Final Integration**

- [ ] **Port `AccountingRulesManager`:**
  - [ ] Create `rotki2/accounting/rules.py`.
  - [ ] Copy `AccountingRulesManager` from `rotkehlchen/accounting/rules.py`.
  - [ ] Refactor its `__init__` to take the new `DatabaseService` and `EVMAccountingAggregator`.
  - [ ] Update `_query_db_rules` to use the `AccountingRuleRepository` instead of direct DB calls.
- [ ] **Port `EventsAccountant`:**
  - [ ] Create `rotki2/accounting/history_base_entries.py`.
  - [ ] Copy `EventsAccountant` from `rotkehlchen/accounting/history_base_entries.py`.
  - [ ] Refactor its `__init__` and `reset` methods to use the new `AccountingRulesManager`.
  - [ ] The `process` method is the core logic. It determines how to handle different event types. This logic must be carefully ported. The calls to `pot.add_in_event` and `pot.add_out_event` will now need to be `await`ed.
- [ ] **Create the `AccountingService`:**
  - [ ] In `rotki2/api/v2/services/accounting.py`, create the main `AccountingService`.
  - [ ] This service will be injected with the `Accountant` and `AccountingRuleRepository`.
  - [ ] It will expose high-level methods like `generate_pnl_report`, `get_accounting_rules`, `add_accounting_rule`, etc., which will be called by the API router.
- [ ] **Update API Router:**
  - [ ] Go to `rotki2/api/v2/routers/accounting.py`.
  - [ ] Ensure the endpoints correctly call the new methods on your `AccountingService`. For example, the `generate_report` endpoint should call a method like `accounting_service.start_pnl_report_generation(...)`.

---

### **Phase 6: Testing and Validation**

- [ ] **Write Unit Tests:**
  - [ ] Create `rotki2/tests/unit/accounting/test_cost_basis.py` and write tests for each cost basis method.
  - [ ] Create `rotki2/tests/unit/accounting/test_pot.py` and test the `AccountingPot`'s async methods.
  - [ ] Create `rotki2/tests/unit/accounting/test_accountant.py` to test the main `Accountant` orchestration.
- [ ] **Write Integration Tests:**
  - [ ] Create `rotki2/tests/integration/test_accounting_service.py`.
  - [ ] Write tests that call the `AccountingService` and verify that the correct data is written to the database via the repositories. Use a real (in-memory) async database session for these tests.
- [ ] **Manual Verification:**
  - [ ] Use the `demo_v2_api.py` or a similar script to manually trigger an accounting run through the new API endpoints.
  - [ ] Compare the generated report with a report from the v1 application using the same input data to ensure the results are identical.

---

### **Definition of Done**

- [ ] All classes and functions from `rotkehlchen/accounting/` have been ported to `rotki2/accounting/`.
- [ ] All ported code is fully asynchronous, using `async/await` and `anyio` where appropriate.
- [ ] All direct database access has been replaced by calls to the appropriate repositories (e.g., `AccountingRuleRepository`, `ReportsRepository`).
- [ ] The new `AccountingService` correctly orchestrates the `Accountant` and its components.
- [ ] Unit and integration tests for the new accounting module are written and pass.
- [ ] A full accounting run on a sample dataset produces the same P&L report as the v1 system.
