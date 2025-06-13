## **Project Rewrite: `chain/` Package Migration Checklist**

This checklist will guide you through migrating the legacy `chain/` package to our new, modern architecture. Follow these steps in order. Each step builds on the last.

### **Phase 1: Core Service and Client Infrastructure**

Build the reusable components for the service layer.

- [x] **Create Base Node Client:** In `rotki2/services/chains/common/node_client.py`, create a base class for interacting with RPC nodes using `httpx`.

  - It should accept an `httpx.AsyncClient` in its `__init__`.
  - It should have a `post` method that handles the basic JSON-RPC 2.0 structure, error handling, and retries.

- [x] **Create Base EVM Service:** In `rotki2/services/chains/common/evm_service.py`, create a `BaseEvmService` to hold logic shared across all EVM chains.

  - Initially, it can be a simple placeholder class. You will add shared logic here as you refactor multiple chains.

- [x] **Refactor Decoding Logic:**
  - Create a `DecodingService` in `rotki2/services/chains/common/decoding_service.py`.
  - The old `EVMTransactionDecoder` logic will live here.
  - The protocol-specific decoders (e.g., Uniswap, Aave) will be refactored into stateless helper functions or classes that this service calls. They will no longer hold state.

### **Phase 2: Migrating Chains (One by One)**

This is the main part of the work. **Complete all steps for one chain before moving to the next.** We'll use **Optimism** as the first example.

#### **Step 2.1: Migrate Optimism**

- [x] **Create `OptimismNodeClient`:**

  - In `rotki2/services/chains/optimism/optimism_node_client.py`, create `OptimismNodeClient` that inherits from `BaseNodeClient`.
  - Migrate methods from the old `OptimismInquirer` (`rotkehlchen/chain/optimism/node_inquirer.py`).
  - Replace all `gevent`-based HTTP requests with `await self.http_client.post(...)`.
  - Remove all database interaction logic from this class. Its only job is to talk to the Optimism RPC node.

- [x] **Create `OptimismRepository`:**

  - In `rotki2/db/repositories/optimism_repository.py`, create the `OptimismRepository`.
  - It will take an `AsyncSession` in its `__init__`.
  - Migrate all Optimism-specific SQL queries from the old codebase, rewriting them using SQLAlchemy's async API (`await session.exec(...)`).

- [x] **Create `OptimismService`:**

  - In `rotki2/services/chains/optimism/optimism_service.py`, create the `OptimismService`.
  - The service's `__init__` will accept `node_client: OptimismNodeClient` and `repository: OptimismRepository`.
  - Move the business logic from `OptimismManager` and `OptimismInquirer` here.
  - Refactor methods to be `async`.
  - Replace direct database calls with `await self.repository.*` methods.
  - Replace direct RPC calls with `await self.node_client.*` methods.
  - The logic from `OptimismTransactionDecoder` and its protocol-specific sub-decoders will be integrated here or in a dedicated `OptimismDecodingService`.

- [x] **Create Dependency Injection Provider:**
  - In a new file `rotki2/api/dependencies.py`, create a provider function to instantiate and yield the `OptimismService`.
  ```python
  # rotki2/api/dependencies.py
  async def get_optimism_service(session: AsyncSession = Depends(get_session)):
      # ... setup client and repo ...
      yield OptimismService(node_client=..., repository=...)
  ```

#### **Step 2.2: Repeat for All Other Chains**

Repeat the steps from 2.1 for every other chain in the `rotkehlchen/chain/` directory.

##### **Ethereum Migration**

- [x] **Create `EthereumNodeClient`:**
  - In `rotki2/services/chains/ethereum/ethereum_node_client.py`
  - Inherit from `BaseNodeClient`
  - Include ENS support methods
  - Include ETH2 deposit tracking
  - Archive node check constants

- [x] **Create `EthereumRepository`:**
  - In `rotki2/db/repositories/ethereum_repository.py`
  - Handle ETH2 deposit data
  - ENS name mappings
  - Transaction and receipt storage

- [x] **Create `EthereumService`:**
  - In `rotki2/services/chains/ethereum/ethereum_service.py`
  - ENS reverse lookup functionality
  - ETH2 deposit tracking
  - Integration with multiple node providers

- [x] **Update DI provider:**
  - Add `get_ethereum_service` to dependencies.py

##### **Polygon PoS Migration**

- [ ] **Create `PolygonPosNodeClient`:**
  - In `rotki2/services/chains/polygon/polygon_node_client.py`
  - Inherit from `BaseNodeClient`
  - Polygon-specific constants

- [ ] **Create `PolygonRepository`:**
  - In `rotki2/db/repositories/polygon_repository.py`
  - Standard EVM repository functionality

- [ ] **Create `PolygonService`:**
  - In `rotki2/services/chains/polygon/polygon_service.py`
  - Bridge transaction handling

- [ ] **Update DI provider**

##### **Arbitrum One Migration**

- [ ] **Create `ArbitrumNodeClient`:**
  - In `rotki2/services/chains/arbitrum/arbitrum_node_client.py`
  - Inherit from L2 with L1 fees base (like Optimism)
  - Arbitrum-specific constants

- [ ] **Create `ArbitrumRepository`:**
  - In `rotki2/db/repositories/arbitrum_repository.py`
  - Include L1 fee tracking

- [ ] **Create `ArbitrumService`:**
  - In `rotki2/services/chains/arbitrum/arbitrum_service.py`
  - L1 fee calculations
  - Nitro upgrade handling

- [ ] **Update DI provider**

##### **Base Migration**

- [ ] **Create `BaseNodeClient`:**
  - In `rotki2/services/chains/base/base_node_client.py`
  - Inherit from L2 with L1 fees base
  - Base-specific constants

- [ ] **Create `BaseRepository`:**
  - In `rotki2/db/repositories/base_repository.py`

- [ ] **Create `BaseService`:**
  - In `rotki2/services/chains/base/base_service.py`

- [ ] **Update DI provider**

##### **Other EVM Chains**

- [ ] **Migrate Gnosis:**
  - Create node client, repository, service
  - Include xDAI bridge support

- [ ] **Migrate Scroll:**
  - Create node client, repository, service  
  - L2 with L1 fees support

- [ ] **Migrate Binance Smart Chain:**
  - Create node client, repository, service
  - BSC-specific token list

##### **Non-EVM Chains**

- [ ] **Migrate Bitcoin:**
  - `BitcoinNodeClient` using block explorers
  - `BitcoinRepository` for xpub data
  - `BitcoinService` for address derivation

- [ ] **Migrate Substrate (Kusama, Polkadot):**
  - `SubstrateClient` using httpx
  - `SubstrateRepository`
  - `SubstrateService`

- [ ] **Migrate ZKSync Lite:**
  - `ZksyncLiteClient` using httpx
  - `ZksyncLiteRepository`
  - `ZksyncLiteService`

### **Phase 3: Refactor the `ChainsAggregator`**

Deconstruct the central coordinator and replace it with a service that leverages the new, independent chain services.

- [ ] **Create `ChainsAggregatorService`:**

  - In `rotki2/services/chains/aggregator_service.py`.
  - Inject all the individual chain services into its `__init__` (e.g., `optimism_service: OptimismService`, `ethereum_service: EthereumService`, etc.).

- [ ] **Refactor `query_balances`:**

  - The `query_balances` method in the new service will no longer contain complex logic.
  - It will use `anyio.create_task_group()` to concurrently call the `get_balances` method on each injected chain service.
  - It will aggregate the results from all services into a single response structure.

- [ ] **Refactor `modify_blockchain_accounts`:**
  - This method will now call the appropriate service based on the `blockchain` parameter (e.g., `self.bitcoin_service.add_account(...)`).

### **Phase 4: Finalization & API Integration**

Expose the new services through the FastAPI layer.

- [ ] **Create Chain API Endpoints:**

  - In `rotki2/api/v2/routers/`, create router files like `chains.py`.
  - Add endpoints like `GET /chains/{chain_name}/balance/{address}`.
  - Use `Depends` to inject the appropriate service (`get_optimism_service`, etc.).
  - The endpoint function will be a simple one-liner: `return await service.get_balance(address)`.

- [ ] **Write Unit and Integration Tests:**

  - For each new service, write unit tests. Mock the node clients and repositories to test the business logic in isolation.
  - Write integration tests for the FastAPI endpoints. These tests will hit a real (test) database and can use `httpx.MockTransport` or other tools to mock external RPC calls.

- [ ] **Cleanup:** Once a chain's functionality is fully migrated, tested, and confirmed to be working, delete the corresponding files from the old `rotkehlchen/chain/` directory.

---

By following this granular checklist, you can methodically work through the migration one piece at a time, ensuring that each component is correctly refactored into the new, clean architecture. Good luck
