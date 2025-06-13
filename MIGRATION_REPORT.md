# Rotkehlchen API V2 Migration Status

_Last updated: 2025-06-13 11:10:17 UTC_

---

## High-Level Summary

| Area                        | Status      | Notes                                    |
| --------------------------- | ----------- | ---------------------------------------- |
| **API Endpoint Migration**  | 30%         | 98 of 328 v1 endpoints migrated |
| **Legacy Dependency Score** | 23          | 23 legacy imports found in v2 code |
| **Architecture Health**     | ⚠️ 93 Alerts | 93 files have incorrect dependencies |


---

## 1. API Endpoint Migration Details

- **Total V1 Endpoints:** 328
- **Migrated:** 98
- **Pending:** 230
- **Migration Progress:** 29.9%

<details>
<summary><b>❌ Endpoints Pending Migration (Click to expand)</b></summary>

| Method | Endpoint |
|--------|----------|
| DELETE | `/avatars/ens/{ens_name}` |
| DELETE | `/balances/blockchains/{blockchain}` |
| DELETE | `/blockchains/eth/modules/{module_name}/data` |
| DELETE | `/blockchains/eth/modules/{module}/balances` |
| DELETE | `/blockchains/eth/modules/{module}/stats` |
| DELETE | `/blockchains/eth/modules/{module}/v{version}/balances` |
| DELETE | `/blockchains/type/{chain_type}/accounts` |
| DELETE | `/blockchains/{blockchain}/nodes` |
| DELETE | `/blockchains/{blockchain}/tokens/detect` |
| DELETE | `/blockchains/{blockchain}/xpub` |
| DELETE | `/cache/{cache_type}/clear` |
| DELETE | `/exchanges/binance/pairs/{name}` |
| DELETE | `/exchanges/data/{location}` |
| DELETE | `/exchanges/{location}/savings` |
| DELETE | `/oracles/{oracle}/cache` |
| DELETE | `/snapshots/{timestamp}` |
| DELETE | `/tasks/{task_id}` |
| DELETE | `/users/{name}` |
| DELETE | `/users/{name}/password` |
| GET | `/accounting/rules/export` |
| GET | `/accounting/rules/import` |
| GET | `/accounting/rules/info` |
| GET | `/actions/ignored` |
| GET | `/airdrops/metadata` |
| GET | `/assets` |
| GET | `/assets/counterpartymappings` |
| GET | `/assets/custom/types` |
| GET | `/assets/evm/spam` |
| GET | `/assets/icon/modify` |
| GET | `/assets/ignored` |
| GET | `/assets/ignored/whitelist` |
| GET | `/assets/locationmappings` |
| GET | `/assets/mappings` |
| GET | `/assets/prices/historical` |
| GET | `/assets/prices/latest/all` |
| GET | `/assets/replace` |
| GET | `/assets/search/levenshtein` |
| GET | `/assets/types` |
| GET | `/assets/updates` |
| GET | `/assets/user` |
| GET | `/balances/blockchains/{blockchain}` |
| GET | `/balances/historical/asset` |
| GET | `/balances/historical/asset/prices` |
| GET | `/balances/historical/netvalue` |
| GET | `/blockchains/eth/airdrops` |
| GET | `/blockchains/eth/modules` |
| GET | `/blockchains/eth/modules/data` |
| GET | `/blockchains/eth/modules/loopring/balances` |
| GET | `/blockchains/eth/modules/pickle/dill` |
| GET | `/blockchains/eth/modules/{module_name}/data` |
| GET | `/blockchains/eth/modules/{module}/balances` |
| GET | `/blockchains/eth/modules/{module}/stats` |
| GET | `/blockchains/eth/modules/{module}/v{version}/balances` |
| GET | `/blockchains/eth2/stake/events` |
| GET | `/blockchains/evm/accounts` |
| GET | `/blockchains/evm/all` |
| GET | `/blockchains/evm/erc20details` |
| GET | `/blockchains/evm/transactions/add-hash` |
| GET | `/blockchains/evm/transactions/decode` |
| GET | `/blockchains/evm/transactions/refetch` |
| GET | `/blockchains/evmlike/transactions` |
| GET | `/blockchains/evmlike/transactions/decode` |
| GET | `/blockchains/transactions` |
| GET | `/blockchains/type/{chain_type}/accounts` |
| GET | `/blockchains/{blockchain}/nodes` |
| GET | `/blockchains/{blockchain}/tokens/detect` |
| GET | `/blockchains/{blockchain}/xpub` |
| GET | `/cache/{cache_type}/clear` |
| GET | `/calendar` |
| GET | `/calendar/reminders` |
| GET | `/exchange_rates` |
| GET | `/exchanges/binance/pairs` |
| GET | `/exchanges/binance/pairs/{name}` |
| GET | `/exchanges/data` |
| GET | `/exchanges/data/{location}` |
| GET | `/exchanges/{location}/savings` |
| GET | `/external_services` |
| GET | `/history` |
| GET | `/history/actionable_items` |
| GET | `/history/debug` |
| GET | `/history/download` |
| GET | `/history/events/counterparties` |
| GET | `/history/events/details` |
| GET | `/history/events/export` |
| GET | `/history/events/export/download` |
| GET | `/history/events/products` |
| GET | `/history/events/query` |
| GET | `/history/events/query/exchange` |
| GET | `/history/events/type_mappings` |
| GET | `/history/skipped_external_events` |
| GET | `/import` |
| GET | `/locations/all` |
| GET | `/locations/associated` |
| GET | `/messages` |
| GET | `/notes` |
| GET | `/oracles` |
| GET | `/oracles/{oracle}/cache` |
| GET | `/periodic` |
| GET | `/premium` |
| GET | `/protocols/data/refresh` |
| GET | `/queried_addresses` |
| GET | `/settings/configuration` |
| GET | `/snapshots` |
| GET | `/snapshots/{timestamp}` |
| GET | `/staking/kraken` |
| GET | `/statistics/wrap` |
| GET | `/tags` |
| GET | `/tasks` |
| GET | `/tasks/{task_id}` |
| GET | `/users/{name}` |
| GET | `/users/{name}/password` |
| GET | `/wallet/balance` |
| GET | `/wallet/interacted` |
| GET | `/wallet/transfer/native` |
| GET | `/wallet/transfer/token` |
| POST | `/accounting/rules/export` |
| POST | `/accounting/rules/import` |
| POST | `/accounting/rules/info` |
| POST | `/actions/ignored` |
| POST | `/airdrops/metadata` |
| POST | `/assets` |
| POST | `/assets/counterpartymappings` |
| POST | `/assets/custom/types` |
| POST | `/assets/evm/spam` |
| POST | `/assets/icon/modify` |
| POST | `/assets/ignored` |
| POST | `/assets/ignored/whitelist` |
| POST | `/assets/locationmappings` |
| POST | `/assets/mappings` |
| POST | `/assets/prices/historical` |
| POST | `/assets/prices/latest/all` |
| POST | `/assets/replace` |
| POST | `/assets/search/levenshtein` |
| POST | `/assets/types` |
| POST | `/assets/updates` |
| POST | `/assets/user` |
| POST | `/balances/historical/asset` |
| POST | `/balances/historical/asset/prices` |
| POST | `/balances/historical/netvalue` |
| POST | `/blockchains/eth/airdrops` |
| POST | `/blockchains/eth/modules` |
| POST | `/blockchains/eth/modules/data` |
| POST | `/blockchains/eth/modules/liquity/balances` |
| POST | `/blockchains/eth/modules/liquity/pool` |
| POST | `/blockchains/eth/modules/liquity/staking` |
| POST | `/blockchains/eth/modules/loopring/balances` |
| POST | `/blockchains/eth/modules/pickle/dill` |
| POST | `/blockchains/eth/modules/{module_name}/data` |
| POST | `/blockchains/eth/modules/{module}/balances` |
| POST | `/blockchains/eth/modules/{module}/stats` |
| POST | `/blockchains/eth/modules/{module}/v{version}/balances` |
| POST | `/blockchains/eth2/stake/dailystats` |
| POST | `/blockchains/eth2/stake/events` |
| POST | `/blockchains/evm/accounts` |
| POST | `/blockchains/evm/all` |
| POST | `/blockchains/evm/erc20details` |
| POST | `/blockchains/evm/transactions` |
| POST | `/blockchains/evm/transactions/add-hash` |
| POST | `/blockchains/evm/transactions/refetch` |
| POST | `/blockchains/evmlike/transactions` |
| POST | `/blockchains/evmlike/transactions/decode` |
| POST | `/blockchains/supported` |
| POST | `/blockchains/transactions` |
| POST | `/blockchains/type/{chain_type}/accounts` |
| POST | `/blockchains/{blockchain}/nodes` |
| POST | `/blockchains/{blockchain}/tokens/detect` |
| POST | `/blockchains/{blockchain}/xpub` |
| POST | `/cache/{cache_type}/clear` |
| POST | `/calendar` |
| POST | `/calendar/reminders` |
| POST | `/database/backups` |
| POST | `/database/info` |
| POST | `/exchange_rates` |
| POST | `/exchanges/binance/pairs` |
| POST | `/exchanges/data` |
| POST | `/exchanges/{location}/savings` |
| POST | `/external_services` |
| POST | `/history/actionable_items` |
| POST | `/history/debug` |
| POST | `/history/download` |
| POST | `/history/events/counterparties` |
| POST | `/history/events/details` |
| POST | `/history/events/export` |
| POST | `/history/events/export/download` |
| POST | `/history/events/products` |
| POST | `/history/events/query` |
| POST | `/history/events/query/exchange` |
| POST | `/history/events/type_mappings` |
| POST | `/history/skipped_external_events` |
| POST | `/locations/all` |
| POST | `/locations/associated` |
| POST | `/messages` |
| POST | `/notes` |
| POST | `/oracles` |
| POST | `/oracles/{oracle}/cache` |
| POST | `/periodic` |
| POST | `/premium` |
| POST | `/premium/sync` |
| POST | `/protocols/data/refresh` |
| POST | `/queried_addresses` |
| POST | `/settings/configuration` |
| POST | `/snapshots` |
| POST | `/staking/kraken` |
| POST | `/statistics/balance` |
| POST | `/statistics/wrap` |
| POST | `/tags` |
| POST | `/tasks` |
| POST | `/wallet/balance` |
| POST | `/wallet/interacted` |
| POST | `/wallet/transfer/native` |
| POST | `/wallet/transfer/token` |
| PUT | `/avatars/ens/{ens_name}` |
| PUT | `/balances/blockchains/{blockchain}` |
| PUT | `/blockchains/eth/modules/{module_name}/data` |
| PUT | `/blockchains/eth/modules/{module}/balances` |
| PUT | `/blockchains/eth/modules/{module}/stats` |
| PUT | `/blockchains/eth/modules/{module}/v{version}/balances` |
| PUT | `/blockchains/type/{chain_type}/accounts` |
| PUT | `/blockchains/{blockchain}/accounts` |
| PUT | `/blockchains/{blockchain}/nodes` |
| PUT | `/blockchains/{blockchain}/tokens/detect` |
| PUT | `/blockchains/{blockchain}/xpub` |
| PUT | `/cache/{cache_type}/clear` |
| PUT | `/exchanges/binance/pairs/{name}` |
| PUT | `/exchanges/data/{location}` |
| PUT | `/exchanges/{location}/savings` |
| PUT | `/oracles/{oracle}/cache` |
| PUT | `/snapshots/{timestamp}` |
| PUT | `/tasks/{task_id}` |
| PUT | `/users/{name}` |

</details>

<details>
<summary><b>✅ Successfully Migrated Endpoints (Click to expand)</b></summary>

| Method | Endpoint |
|--------|----------|
| DELETE | `/blockchains/{blockchain}/accounts` |
| DELETE | `/exchanges/balances/{location}` |
| DELETE | `/names/addressbook/{book_type}` |
| DELETE | `/reports/{report_id}` |
| DELETE | `/reports/{report_id}/data` |
| GET | `/accounting/rules` |
| GET | `/accounting/rules/conflicts` |
| GET | `/assets/all` |
| GET | `/assets/custom` |
| GET | `/assets/prices/latest` |
| GET | `/assets/search` |
| GET | `/avatars/ens/{ens_name}` |
| GET | `/balances` |
| GET | `/balances/blockchains` |
| GET | `/balances/historical` |
| GET | `/balances/manual` |
| GET | `/blockchains/eth/modules/liquity/balances` |
| GET | `/blockchains/eth/modules/liquity/pool` |
| GET | `/blockchains/eth/modules/liquity/staking` |
| GET | `/blockchains/eth2/stake/dailystats` |
| GET | `/blockchains/eth2/stake/performance` |
| GET | `/blockchains/eth2/validators` |
| GET | `/blockchains/evm/transactions` |
| GET | `/blockchains/supported` |
| GET | `/blockchains/{blockchain}/accounts` |
| GET | `/database/backups` |
| GET | `/database/info` |
| GET | `/defi/metadata` |
| GET | `/exchanges` |
| GET | `/exchanges/balances` |
| GET | `/exchanges/balances/{location}` |
| GET | `/history/events` |
| GET | `/history/export` |
| GET | `/history/status` |
| GET | `/info` |
| GET | `/names` |
| GET | `/names/addressbook/{book_type}` |
| GET | `/names/ens/resolve` |
| GET | `/names/ens/reverse` |
| GET | `/nfts` |
| GET | `/nfts/balances` |
| GET | `/nfts/prices` |
| GET | `/ping` |
| GET | `/premium/sync` |
| GET | `/reports` |
| GET | `/reports/{report_id}` |
| GET | `/reports/{report_id}/data` |
| GET | `/settings` |
| GET | `/statistics/balance` |
| GET | `/statistics/netvalue` |
| GET | `/statistics/renderer` |
| GET | `/statistics/value_distribution` |
| GET | `/users` |
| GET | `/watchers` |
| POST | `/accounting/rules` |
| POST | `/accounting/rules/conflicts` |
| POST | `/assets/all` |
| POST | `/assets/custom` |
| POST | `/assets/prices/latest` |
| POST | `/assets/search` |
| POST | `/balances` |
| POST | `/balances/blockchains` |
| POST | `/balances/historical` |
| POST | `/balances/manual` |
| POST | `/blockchains/eth2/stake/performance` |
| POST | `/blockchains/eth2/validators` |
| POST | `/blockchains/evm/transactions/decode` |
| POST | `/blockchains/{blockchain}/accounts` |
| POST | `/defi/metadata` |
| POST | `/exchanges` |
| POST | `/exchanges/balances` |
| POST | `/history` |
| POST | `/history/events` |
| POST | `/history/export` |
| POST | `/history/status` |
| POST | `/import` |
| POST | `/info` |
| POST | `/names` |
| POST | `/names/ens/resolve` |
| POST | `/names/ens/reverse` |
| POST | `/nfts` |
| POST | `/nfts/balances` |
| POST | `/nfts/prices` |
| POST | `/ping` |
| POST | `/reports` |
| POST | `/reports/{report_id}/data` |
| POST | `/settings` |
| POST | `/statistics/netvalue` |
| POST | `/statistics/renderer` |
| POST | `/statistics/value_distribution` |
| POST | `/users` |
| POST | `/users/{name}/password` |
| POST | `/watchers` |
| PUT | `/exchanges/balances/{location}` |
| PUT | `/names/addressbook/{book_type}` |
| PUT | `/reports/{report_id}` |
| PUT | `/reports/{report_id}/data` |
| PUT | `/users/{name}/password` |

</details>

<details>
<summary><b>✨ New V2 Endpoints (Click to expand)</b></summary>

| Method | Endpoint |
|--------|----------|
| DELETE | `/accounting/rules/linked` |
| DELETE | `/accounting/rules/{rule_id}` |
| DELETE | `/auth/api-keys/{key_id}` |
| DELETE | `/blockchain/{blockchain}/accounts` |
| DELETE | `/blockchains/eth2/validators/{validator_id}` |
| DELETE | `/exchanges/{name}` |
| DELETE | `/history/events/{event_id}` |
| DELETE | `/nfts/prices/manual/{asset}` |
| DELETE | `/watchers` |
| GET | `/accounting/rules/linked` |
| GET | `/assets/evm/erc20/{chain_id}/{address}` |
| GET | `/auth/api-keys` |
| GET | `/balances/exchanges` |
| GET | `/blockchain/evm/transactions` |
| GET | `/blockchain/supported` |
| GET | `/blockchain/{blockchain}/accounts` |
| GET | `/blockchains/eth2/stake/daily-stats` |
| GET | `/blockchains/eth2/stake/deposits` |
| GET | `/data/database/backups` |
| GET | `/data/database/info` |
| GET | `/defi/blockchains/eth/modules/liquity/balances` |
| GET | `/defi/blockchains/eth/modules/liquity/pool` |
| GET | `/defi/blockchains/eth/modules/liquity/staking` |
| GET | `/defi/blockchains/eth/modules/liquity/stats` |
| GET | `/defi/blockchains/{blockchain}/modules/{module}/balances` |
| GET | `/defi/blockchains/{blockchain}/modules/{module}/stats` |
| GET | `/defi/blockchains/{blockchain}/modules/{module}/v{version}/balances` |
| GET | `/names/avatars/ens/{ens_name}` |
| GET | `/statistics/balance/{asset}` |
| GET | `/statistics/location_distribution` |
| GET | `/watchers/sync/status` |
| PATCH | `/names/addressbook/{book_type}` |
| PATCH | `/settings` |
| PATCH | `/users/{username}/password` |
| PATCH | `/watchers` |
| POST | `/accounting/rules/linked` |
| POST | `/auth/api-keys` |
| POST | `/auth/login` |
| POST | `/blockchain/evm/transactions/decode` |
| POST | `/blockchain/{blockchain}/accounts` |
| POST | `/data/database/backup` |
| POST | `/data/database/restore` |
| POST | `/data/export` |
| POST | `/data/import` |
| POST | `/exchanges/{location}/query` |
| POST | `/history/process` |
| POST | `/names/addressbook/{book_type}` |
| POST | `/nfts/prices/manual` |
| POST | `/users/login` |
| POST | `/users/logout` |
| PUT | `/accounting/rules/{rule_id}` |
| PUT | `/history/events/{event_id}` |
| PUT | `/watchers` |
| PUT | `/watchers/sync` |

</details>



---

## 2. Legacy Data Layer Dependencies

**Overall Legacy Dependency Score:** 23 legacy imports found in v2 codebase

### Files with Legacy Dependencies ⚠️

#### `api/v2/`

**`app.py`** (1 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`

**`dependencies.py`** (1 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`

#### `api/v2/repositories/`

**`globaldb_asset.py`** (1 legacy imports):
  - `from rotkehlchen.db.filtering import AssetsFilterQuery`

**`history.py`** (1 legacy imports):
  - `from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED`

#### `api/v2/routers/`

**`defi.py`** (1 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`

**`names.py`** (2 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`
  - `from rotkehlchen.db.filtering import AddressbookFilterQuery`

**`nfts.py`** (2 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`
  - `from rotkehlchen.db.filtering import NFTFilterQuery`

#### `api/v2/services/`

**`assets.py`** (3 legacy imports):
  - `from rotkehlchen.db.dbhandler import DBHandler`
  - `from rotkehlchen.db.filtering import AssetsFilterQuery, LevenshteinFilterQuery`
  - `from rotkehlchen.db.search_assets import search_assets_levenshtein`

**`blockchain.py`** (1 legacy imports):
  - `from rotkehlchen.db.utils import deserialize_tags_from_db`

**`database.py`** (1 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`

**`defi.py`** (1 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`

**`history.py`** (3 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`
  - `from rotkehlchen.db.filtering import HistoryEventFilterQuery`
  - `from rotkehlchen.db.history_events import DBHistoryEvents`

**`names.py`** (3 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`
  - `from rotkehlchen.db.filtering import AddressbookFilterQuery`
  - `from rotkehlchen.db.repository.addressbook import AddressbookRepository`

**`nfts.py`** (2 legacy imports):
  - `from rotkehlchen.db.drivers.gevent import DBConnection`
  - `from rotkehlchen.db.filtering import NFTFilterQuery`



---

## 3. Architecture Health Check

**Total Violations Found:** 93

### Architecture Violations 🚨

#### Repositories Layer Violations

**`api/v2/repositories/asset.py`** (2 violations):
  - Line 9: `rotkehlchen.api.v2.repositories.base` - Repositories should not import from rotkehlchen.api.v2.repositories.base
  - Line 10: `rotkehlchen.assets.types` - Repositories should not import from rotkehlchen.assets.types

**`api/v2/repositories/asset_ignore.py`** (2 violations):
  - Line 7: `rotkehlchen.api.v2.repositories.base` - Repositories should not import from rotkehlchen.api.v2.repositories.base
  - Line 8: `rotkehlchen.assets.asset` - Repositories should not import from rotkehlchen.assets.asset

**`api/v2/repositories/balance.py`** (1 violations):
  - Line 10: `rotkehlchen.api.v2.repositories.base` - Repositories should not import from rotkehlchen.api.v2.repositories.base

**`api/v2/repositories/balance_source.py`** (5 violations):
  - Line 5: `rotkehlchen.accounting.structures.balance` - Repositories should not import from rotkehlchen.accounting.structures.balance
  - Line 6: `rotkehlchen.assets.asset` - Repositories should not import from rotkehlchen.assets.asset
  - Line 7: `rotkehlchen.fval` - Repositories should not import from rotkehlchen.fval
  - Line 70: `rotkehlchen.fval` - Repositories should not import from rotkehlchen.fval
  - Line 102: `rotkehlchen.inquirer` - Repositories should not import from rotkehlchen.inquirer

**`api/v2/repositories/ens.py`** (1 violations):
  - Line 9: `rotkehlchen.api.v2.repositories.base` - Repositories should not import from rotkehlchen.api.v2.repositories.base

**`api/v2/repositories/globaldb_asset.py`** (3 violations):
  - Line 7: `rotkehlchen.assets.asset` - Repositories should not import from rotkehlchen.assets.asset
  - Line 8: `rotkehlchen.db.filtering` - Repositories should not import from rotkehlchen.db.filtering
  - Line 9: `rotkehlchen.globaldb.handler` - Repositories should not import from rotkehlchen.globaldb.handler

**`api/v2/repositories/history.py`** (3 violations):
  - Line 12: `rotkehlchen.api.v2.repositories.base` - Repositories should not import from rotkehlchen.api.v2.repositories.base
  - Line 14: `rotkehlchen.db.constants` - Repositories should not import from rotkehlchen.db.constants
  - Line 23: `rotkehlchen.history.events.structures.base` - Repositories should not import from rotkehlchen.history.events.structures.base

**`api/v2/repositories/user.py`** (1 violations):
  - Line 9: `rotkehlchen.api.v2.repositories.base` - Repositories should not import from rotkehlchen.api.v2.repositories.base

#### Routers Layer Violations

**`api/v2/routers/assets.py`** (2 violations):
  - Line 9: `rotkehlchen.assets.asset` - Routers should not import from rotkehlchen.assets.asset
  - Line 10: `rotkehlchen.assets.types` - Routers should not import from rotkehlchen.assets.types

**`api/v2/routers/balances.py`** (5 violations):
  - Line 16: `rotkehlchen.assets.asset` - Routers should not import from rotkehlchen.assets.asset
  - Line 17: `rotkehlchen.fval` - Routers should not import from rotkehlchen.fval
  - Line 21: `rotkehlchen.api.websockets.notifier` - Routers should not import from rotkehlchen.api.websockets.notifier
  - Line 22: `rotkehlchen.chain.aggregator` - Routers should not import from rotkehlchen.chain.aggregator
  - Line 23: `rotkehlchen.exchanges.manager` - Routers should not import from rotkehlchen.exchanges.manager

**`api/v2/routers/blockchain.py`** (2 violations):
  - Line 13: `rotkehlchen.chain.constants` - Routers should not import from rotkehlchen.chain.constants
  - Line 14: `rotkehlchen.chain.evm.types` - Routers should not import from rotkehlchen.chain.evm.types

**`api/v2/routers/defi.py`** (4 violations):
  - Line 13: `rotkehlchen.chain.evm.types` - Routers should not import from rotkehlchen.chain.evm.types
  - Line 14: `rotkehlchen.db.drivers.gevent` - Routers should not import from rotkehlchen.db.drivers.gevent
  - Line 16: `rotkehlchen.premium.premium` - Routers should not import from rotkehlchen.premium.premium
  - Line 20: `rotkehlchen.chain.aggregator` - Routers should not import from rotkehlchen.chain.aggregator

**`api/v2/routers/exchanges.py`** (1 violations):
  - Line 13: `rotkehlchen.exchanges.constants` - Routers should not import from rotkehlchen.exchanges.constants

**`api/v2/routers/history.py`** (1 violations):
  - Line 13: `rotkehlchen.history.events.structures.base` - Routers should not import from rotkehlchen.history.events.structures.base

**`api/v2/routers/names.py`** (6 violations):
  - Line 15: `rotkehlchen.chain.evm.types` - Routers should not import from rotkehlchen.chain.evm.types
  - Line 16: `rotkehlchen.db.drivers.gevent` - Routers should not import from rotkehlchen.db.drivers.gevent
  - Line 17: `rotkehlchen.db.filtering` - Routers should not import from rotkehlchen.db.filtering
  - Line 23: `rotkehlchen.chain.aggregator` - Routers should not import from rotkehlchen.chain.aggregator
  - Line 24: `rotkehlchen.data_handler` - Routers should not import from rotkehlchen.data_handler
  - Line 25: `rotkehlchen.rotkehlchen` - Routers should not import from rotkehlchen.rotkehlchen

**`api/v2/routers/nfts.py`** (6 violations):
  - Line 14: `rotkehlchen.chain.ethereum.modules.nft.structures` - Routers should not import from rotkehlchen.chain.ethereum.modules.nft.structures
  - Line 15: `rotkehlchen.db.drivers.gevent` - Routers should not import from rotkehlchen.db.drivers.gevent
  - Line 16: `rotkehlchen.db.filtering` - Routers should not import from rotkehlchen.db.filtering
  - Line 20: `rotkehlchen.chain.aggregator` - Routers should not import from rotkehlchen.chain.aggregator
  - Line 21: `rotkehlchen.data_handler` - Routers should not import from rotkehlchen.data_handler
  - Line 119: `rotkehlchen.chain.evm.types` - Routers should not import from rotkehlchen.chain.evm.types

**`api/v2/routers/reports.py`** (2 violations):
  - Line 18: `rotkehlchen.accounting.accountant` - Routers should not import from rotkehlchen.accounting.accountant
  - Line 19: `rotkehlchen.api.websockets.notifier` - Routers should not import from rotkehlchen.api.websockets.notifier

**`api/v2/routers/users.py`** (3 violations):
  - Line 16: `rotkehlchen.db.settings` - Routers should not import from rotkehlchen.db.settings
  - Line 19: `rotkehlchen.premium.premium` - Routers should not import from rotkehlchen.premium.premium
  - Line 22: `rotkehlchen.rotkehlchen` - Routers should not import from rotkehlchen.rotkehlchen

**`api/v2/routers/watchers.py`** (2 violations):
  - Line 10: `rotkehlchen.premium.premium` - Routers should not import from rotkehlchen.premium.premium
  - Line 13: `rotkehlchen.rotkehlchen` - Routers should not import from rotkehlchen.rotkehlchen

#### Services Layer Violations

**`api/v2/services/assets.py`** (7 violations):
  - Line 5: `rotkehlchen.assets.asset` - Services should not import from rotkehlchen.assets.asset
  - Line 11: `rotkehlchen.assets.resolver` - Services should not import from rotkehlchen.assets.resolver
  - Line 12: `rotkehlchen.assets.types` - Services should not import from rotkehlchen.assets.types
  - Line 15: `rotkehlchen.db.filtering` - Services should not import from rotkehlchen.db.filtering
  - Line 16: `rotkehlchen.db.search_assets` - Services should not import from rotkehlchen.db.search_assets
  - Line 23: `rotkehlchen.inquirer` - Services should not import from rotkehlchen.inquirer
  - Line 28: `rotkehlchen.db.dbhandler` - Services must use repositories instead of DBHandler

**`api/v2/services/balance_aggregator.py`** (1 violations):
  - Line 9: `rotkehlchen.assets.asset` - Services should not import from rotkehlchen.assets.asset

**`api/v2/services/balances.py`** (5 violations):
  - Line 13: `rotkehlchen.assets.asset` - Services should not import from rotkehlchen.assets.asset
  - Line 14: `rotkehlchen.balances.manual` - Services should not import from rotkehlchen.balances.manual
  - Line 15: `rotkehlchen.fval` - Services should not import from rotkehlchen.fval
  - Line 20: `rotkehlchen.api.websockets.notifier` - Services should not import from rotkehlchen.api.websockets.notifier
  - Line 22: `rotkehlchen.exchanges.manager` - Services should not import from rotkehlchen.exchanges.manager

**`api/v2/services/blockchain.py`** (1 violations):
  - Line 6: `rotkehlchen.db.utils` - Services should not import from rotkehlchen.db.utils

**`api/v2/services/database.py`** (1 violations):
  - Line 6: `rotkehlchen.db.drivers.gevent` - Services should not import from rotkehlchen.db.drivers.gevent

**`api/v2/services/defi.py`** (2 violations):
  - Line 5: `rotkehlchen.db.drivers.gevent` - Services should not import from rotkehlchen.db.drivers.gevent
  - Line 13: `rotkehlchen.premium.premium` - Services should not import from rotkehlchen.premium.premium

**`api/v2/services/history.py`** (7 violations):
  - Line 4: `rotkehlchen.assets.asset` - Services should not import from rotkehlchen.assets.asset
  - Line 5: `rotkehlchen.db.drivers.gevent` - Services should not import from rotkehlchen.db.drivers.gevent
  - Line 6: `rotkehlchen.db.filtering` - Services should not import from rotkehlchen.db.filtering
  - Line 7: `rotkehlchen.db.history_events` - Services must use repositories for history events
  - Line 9: `rotkehlchen.fval` - Services should not import from rotkehlchen.fval
  - Line 16: `rotkehlchen.api.websockets.notifier` - Services should not import from rotkehlchen.api.websockets.notifier
  - Line 18: `rotkehlchen.tasks.manager` - Services should not import from rotkehlchen.tasks.manager

**`api/v2/services/names.py`** (5 violations):
  - Line 7: `rotkehlchen.db.drivers.gevent` - Services should not import from rotkehlchen.db.drivers.gevent
  - Line 8: `rotkehlchen.db.filtering` - Services should not import from rotkehlchen.db.filtering
  - Line 19: `rotkehlchen.addressbook.addressbook` - Services should not import from rotkehlchen.addressbook.addressbook
  - Line 21: `rotkehlchen.data_handler` - Services should not import from rotkehlchen.data_handler
  - Line 22: `rotkehlchen.db.repository.addressbook` - Services should not import from rotkehlchen.db.repository.addressbook

**`api/v2/services/nfts.py`** (9 violations):
  - Line 6: `rotkehlchen.db.filtering` - Services should not import from rotkehlchen.db.filtering
  - Line 7: `rotkehlchen.db.drivers.gevent` - Services should not import from rotkehlchen.db.drivers.gevent
  - Line 9: `rotkehlchen.premium.premium` - Services should not import from rotkehlchen.premium.premium
  - Line 15: `rotkehlchen.data_handler` - Services should not import from rotkehlchen.data_handler
  - Line 128: `rotkehlchen.assets.asset` - Services should not import from rotkehlchen.assets.asset
  - Line 129: `rotkehlchen.assets.types` - Services should not import from rotkehlchen.assets.types
  - Line 130: `rotkehlchen.fval` - Services should not import from rotkehlchen.fval
  - Line 148: `rotkehlchen.assets.asset` - Services should not import from rotkehlchen.assets.asset
  - Line 149: `rotkehlchen.assets.types` - Services should not import from rotkehlchen.assets.types

**`api/v2/services/reports.py`** (1 violations):
  - Line 9: `rotkehlchen.api.websockets.notifier` - Services should not import from rotkehlchen.api.websockets.notifier

**`api/v2/services/statistics.py`** (1 violations):
  - Line 5: `rotkehlchen.fval` - Services should not import from rotkehlchen.fval

**`api/v2/services/watchers.py`** (1 violations):
  - Line 8: `rotkehlchen.premium.premium` - Services should not import from rotkehlchen.premium.premium



---

## Next Steps

Based on this analysis:

1. **Complete endpoint migration**: 230 endpoints still need to be migrated to v2
2. **Eliminate legacy dependencies**: Refactor 14 files to use the new repository pattern
3. **Fix architecture violations**: Address 93 violations to maintain clean architecture
