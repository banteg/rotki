### **Rotki v1 to v2 API Endpoint Migration Checklist**

#### **Users & Authentication**

- [x] `GET /api/1/users` (List all user accounts) ✅ Migrated to `GET /api/v2/users/`
- [x] `PUT /api/1/users` (Create a new user) ✅ Migrated to `POST /api/v2/users/`
- [x] `GET /api/1/users/<string:name>` (Login user - Note: v2 uses `POST /api/v2/auth/login`) ✅ Migrated to `POST /api/v2/users/login`
- [~] `PATCH /api/1/users/<string:name>` (Set premium credentials or logout) ⚠️ Logout migrated to `POST /api/v2/users/logout`, premium credentials still needed
- [x] `PATCH /api/1/users/<string:name>/password` (Change user password) ✅ Migrated to `PATCH /api/v2/users/{username}/password`
- [x] `DELETE /api/1/premium` (Remove premium API key) ✅ Migrated to `DELETE /api/v2/premium/`
- [x] `PUT /api/1/premium/sync` (Trigger premium data sync) ✅ Migrated to `PUT /api/v2/premium/sync`

#### **Settings & Configuration**

- [x] `GET /api/1/settings` (Get user settings) ✅ Migrated to `GET /api/v2/settings/`
- [x] `PUT /api/1/settings` (Set user settings) ✅ Migrated to `PATCH /api/v2/settings/`
- [x] `GET /api/1/settings/configuration` (Get runtime config arguments) ✅ Migrated to `GET /api/v2/settings/configuration`

#### **Async Tasks**

- [x] `GET /api/1/tasks` (Get all async tasks) ✅ Migrated to `GET /api/v2/tasks/`
- [x] `GET /api/1/tasks/<int:task_id>` (Get a specific async task outcome) ✅ Migrated to `GET /api/v2/tasks/{task_id}`
- [x] `DELETE /api/1/tasks/<int:task_id>` (Cancel/delete an async task) ✅ Migrated to `DELETE /api/v2/tasks/{task_id}`

#### **External Services & Oracles**

- [x] `GET /api/1/external_services` (Get all external service credentials) ✅ Migrated to `GET /api/v2/external_services/`
- [x] `PUT /api/1/external_services` (Add external service credentials) ✅ Migrated to `PUT /api/v2/external_services/`
- [x] `DELETE /api/1/external_services` (Remove external service credentials) ✅ Migrated to `DELETE /api/v2/external_services/`
- [x] `GET /api/1/oracles` (Get list of supported oracles) ✅ Migrated to `GET /api/v2/oracles/`
- [x] `GET /api/1/oracles/<string:oracle>/cache` (Get cache for a specific oracle) ✅ Migrated to `GET /api/v2/oracles/{oracle}/cache`
- [x] `POST /api/1/oracles/<string:oracle>/cache` (Create cache for a specific oracle) ✅ Migrated to `POST /api/v2/oracles/{oracle}/cache`
- [x] `DELETE /api/1/oracles/<string:oracle>/cache` (Delete cache for a specific oracle) ✅ Migrated to `DELETE /api/v2/oracles/{oracle}/cache`

#### **Exchanges**

- [x] `GET /api/1/exchanges` (Get connected exchanges) ✅ Migrated to `GET /api/v2/exchanges/`
- [x] `PUT /api/1/exchanges` (Add an exchange) ✅ Migrated to `POST /api/v2/exchanges/`
- [x] `PATCH /api/1/exchanges` (Edit an exchange) ✅ Migrated to `PATCH /api/v2/exchanges/`
- [x] `DELETE /api/1/exchanges` (Remove an exchange) ✅ Migrated to `DELETE /api/v2/exchanges/{name}`
- [x] `GET /api/1/exchanges/balances` (Get all exchange balances) ✅ Migrated to `GET /api/v2/exchanges/balances`
- [x] `GET /api/1/exchanges/balances/<string:location>` (Get balances for a specific exchange) ✅ Migrated to `GET /api/v2/exchanges/balances/{location}`
- [ ] `GET /api/1/exchanges/binance/pairs` (Get all available Binance pairs)
- [ ] `GET /api/1/exchanges/binance/pairs/<string:name>` (Get user-configured Binance pairs)
- [ ] `POST /api/1/exchanges/<string:location>/savings` (Get Binance savings history)
- [x] `DELETE /api/1/exchanges/data` (Purge all exchange data) ✅ Migrated to `DELETE /api/v2/exchanges/data`
- [x] `DELETE /api/1/exchanges/data/<string:location>` (Purge data for a specific exchange) ✅ Migrated to `DELETE /api/v2/exchanges/data/{location}`
- [ ] `POST /api/1/exchanges/events/query` (Query history events for an exchange)

#### **Assets & Pricing**

- [x] `POST /api/1/assets/all` (Query all assets) ✅ Migrated to `POST /api/v2/assets/all`
- [x] `GET /api/1/assets` (Get owned assets) ✅ Migrated to `GET /api/v2/assets/` and `GET /api/v2/assets/user`
- [x] `PUT /api/1/assets/all` (Add a new asset) ✅ Migrated to `PUT /api/v2/assets/all`
- [x] `PATCH /api/1/assets/all` (Edit an existing asset) ✅ Migrated to `PATCH /api/v2/assets/all`
- [x] `DELETE /api/1/assets/all` (Delete a custom asset) ✅ Migrated to `DELETE /api/v2/assets/all`
- [ ] `POST /api/1/assets/mappings` (Get asset mappings)
- [ ] `POST /api/1/assets/search` (Search for an asset by name/symbol)
- [ ] `POST /api/1/assets/search/levenshtein` (Fuzzy search for an asset)
- [ ] `GET /api/1/assets/types` (Get all supported asset types)
- [ ] `PUT /api/1/assets/replace` (Merge two asset entries)
- [ ] `GET /api/1/assets/updates` (Check for remote asset data updates)
- [ ] `POST /api/1/assets/updates` (Perform asset data updates)
- [ ] `DELETE /api/1/assets/updates` (Reset local asset data)
- [ ] `PUT /api/1/assets/user` (Import user-defined assets from a file)
- [ ] `GET /api/1/assets/custom` (Get all custom assets)
- [ ] `PUT /api/1/assets/custom` (Add a new custom asset)
- [ ] `PATCH /api/1/assets/custom` (Edit a custom asset)
- [ ] `DELETE /api/1/assets/custom` (Delete a custom asset)
- [ ] `GET /api/1/assets/custom/types` (Get all custom asset types)
- [x] `GET /api/1/exchange_rates` (Get exchange rates for given pairs) ✅ Migrated to `GET /api/v2/exchange_rates/`
- [ ] `POST /api/1/assets/prices/latest` (Get current prices for a list of assets)
- [ ] `GET /api/1/assets/prices/latest/all` (Get all stored manual latest prices)
- [ ] `PUT /api/1/assets/prices/latest` (Add a manual latest price)
- [ ] `DELETE /api/1/assets/prices/latest` (Delete a manual latest price)
- [ ] `POST /api/1/assets/prices/historical` (Get historical prices for a list of assets and timestamps)
- [ ] `GET /api/1/assets/prices/historical` (Get all stored manual historical prices)
- [ ] `PUT /api/1/assets/prices/historical` (Add a manual historical price)
- [ ] `PATCH /api/1/assets/prices/historical` (Edit a manual historical price)
- [ ] `DELETE /api/1/assets/prices/historical` (Delete a manual historical price)
- [ ] `PUT /api/1/assets/icon/modify` (Upload an asset icon)
- [ ] `POST /api/1/assets/icon/modify` (Upload an asset icon via form)
- [ ] `PATCH /api/1/assets/icon/modify` (Refresh an asset icon from a remote source)
- [ ] `POST /api/1/assets/locationmappings` (Query location asset mappings)
- [ ] `PUT /api/1/assets/locationmappings` (Add location asset mappings)
- [ ] `PATCH /api/1/assets/locationmappings` (Update location asset mappings)
- [ ] `DELETE /api/1/assets/locationmappings` (Delete location asset mappings)
- [ ] `POST /api/1/assets/counterpartymappings` (Query counterparty asset mappings)
- [ ] `PUT /api/1/assets/counterpartymappings` (Add counterparty asset mappings)
- [ ] `PATCH /api/1/assets/counterpartymappings` (Update counterparty asset mappings)
- [ ] `DELETE /api/1/assets/counterpartymappings` (Delete counterparty asset mappings)

#### **Balances**

- [x] `GET /api/1/balances` (Get all balances) ✅ Migrated to `GET /api/v2/balances/`
- [x] `GET /api/1/balances/blockchains` (Get all blockchain balances) ✅ Migrated to `GET /api/v2/balances/blockchains`
- [x] `GET /api/1/balances/blockchains/<string:blockchain>` (Get balances for a specific blockchain) ✅ Migrated to `GET /api/v2/balances/blockchains/{blockchain}`
- [x] `GET /api/1/balances/manual` (Get all manually tracked balances) ✅ Migrated to `GET /api/v2/balances/manual`
- [x] `PUT /api/1/balances/manual` (Add manually tracked balances) ✅ Migrated to `PUT /api/v2/balances/manual`
- [x] `PATCH /api/1/balances/manual` (Edit manually tracked balances) ✅ Migrated to `PATCH /api/v2/balances/manual`
- [x] `DELETE /api/1/balances/manual` (Remove manually tracked balances) ✅ Migrated to `DELETE /api/v2/balances/manual`

#### **Blockchains & EVM**

- [x] `GET /api/1/blockchains/supported` (Get a list of all supported blockchains) ✅ Migrated to `GET /api/v2/blockchain/supported`
- [ ] `POST /api/1/blockchains/transactions` (Query blockchain transactions for a time range)
- [ ] `DELETE /api/1/blockchains/transactions` (Purge transaction data)
- [ ] `GET /api/1/blockchains/evm/all` (Get details for all supported EVM chains)
- [ ] `PUT /api/1/blockchains/evm/transactions` (Decode a given list of EVM transactions)
- [ ] `PUT /api/1/blockchains/evmlike/transactions` (Decode a given list of EVM-like transactions)
- [ ] `POST /api/1/blockchains/evm/transactions/decode` (Decode all pending EVM transactions)
- [ ] `GET /api/1/blockchains/evm/transactions/decode` (Get the count of undecoded EVM transactions)
- [ ] `POST /api/1/blockchains/evmlike/transactions/decode` (Decode all pending EVM-like transactions)
- [ ] `GET /api/1/blockchains/evmlike/transactions/decode` (Get the count of undecoded EVM-like transactions)
- [ ] `GET /api/1/blockchains/evm/erc20details` (Get info for an ERC20 token)
- [ ] `POST /api/1/blockchains/evm/accounts` (Refresh all EVM accounts)
- [ ] `PUT /api/1/blockchains/evm/accounts` (Add EVM accounts)
- [x] `GET /api/1/blockchains/<string:blockchain>/accounts` (Get accounts for a specific blockchain) ✅ Migrated to `GET /api/v2/blockchain/{blockchain}/accounts`
- [x] `PUT /api/1/blockchains/<string:blockchain>/accounts` (Add accounts for a specific blockchain) ✅ Migrated to `POST /api/v2/blockchain/{blockchain}/accounts`
- [x] `PATCH /api/1/blockchains/<string:blockchain>/accounts` (Edit accounts for a specific blockchain) ✅ Migrated to `PATCH /api/v2/blockchain/{blockchain}/accounts`
- [x] `DELETE /api/1/blockchains/<string:blockchain>/accounts` (Delete accounts for a specific blockchain) ✅ Migrated to `DELETE /api/v2/blockchain/{blockchain}/accounts`
- [x] `GET /api/1/blockchains/<string:blockchain>/nodes` (Get RPC nodes for a chain) ✅ Migrated to `GET /api/v2/blockchain/{blockchain}/nodes`
- [x] `PUT /api/1/blockchains/<string:blockchain>/nodes` (Add a new RPC node) ✅ Migrated to `PUT /api/v2/blockchain/{blockchain}/nodes`
- [x] `PATCH /api/1/blockchains/<string:blockchain>/nodes` (Edit an RPC node) ✅ Migrated to `PATCH /api/v2/blockchain/{blockchain}/nodes`
- [x] `DELETE /api/1/blockchains/<string:blockchain>/nodes` (Delete an RPC node) ✅ Migrated to `DELETE /api/v2/blockchain/{blockchain}/nodes`
- [x] `POST /api/1/blockchains/<string:blockchain>/nodes` (Attempt to connect to an RPC node) ✅ Migrated to `POST /api/v2/blockchain/{blockchain}/nodes`
- [ ] `POST /api/1/blockchains/<string:blockchain>/tokens/detect` (Detect tokens for a chain)
- [ ] `PUT /api/1/blockchains/evm/transactions/add-hash` (Add a single transaction by hash)
- [ ] `POST /api/1/blockchains/transactions/refetch` (Force refetch EVM transactions for a time range)

#### **ETH2 Staking**

- [x] `GET /api/1/blockchains/eth2/validators` (Get all tracked ETH2 validators) ✅ Migrated to `GET /api/v2/blockchains/eth2/validators`
- [ ] `PUT /api/1/blockchains/eth2/validators` (Add an ETH2 validator)
- [ ] `PATCH /api/1/blockchains/eth2/validators` (Edit an ETH2 validator)
- [ ] `DELETE /api/1/blockchains/eth2/validators` (Delete an ETH2 validator)
- [ ] `PUT /api/1/blockchains/eth2/stake/performance` (Get ETH2 staking performance)
- [ ] `POST /api/1/blockchains/eth2/stake/dailystats` (Get ETH2 daily staking statistics)
- [ ] `PUT /api/1/blockchains/eth2/stake/events` (Redecode ETH2 block production events)
- [ ] `DELETE /api/1/blockchains/eth2/stake/events` (Reset ETH2 staking data)

#### **BTC / XPUBs**

- [ ] `PUT /api/1/blockchains/<string:blockchain>/xpub` (Add a BTC/BCH xpub)
- [ ] `PATCH /api/1/blockchains/<string:blockchain>/xpub` (Edit a BTC/BCH xpub)
- [ ] `DELETE /api/1/blockchains/<string:blockchain>/xpub` (Delete a BTC/BCH xpub)

#### **History & Accounting**

- [x] `GET /api/1/history` (Process history for a time range) ✅ Migrated to `GET /api/v2/history/` and `POST /api/v2/history/process`
- [ ] `POST /api/1/history/debug` (Export PnL debug data)
- [ ] `PUT /api/1/history/debug` (Import PnL debug data from file path)
- [ ] `PATCH /api/1/history/debug` (Import PnL debug data from file upload)
- [x] `GET /api/1/history/status` (Get history processing status) ✅ Migrated to `GET /api/v2/history/status`
- [x] `GET /api/1/history/export` (Download history as CSV) ✅ Migrated to `GET /api/v2/history/download`
- [x] `POST /api/1/history/events` (Query history events) ✅ Migrated to `GET /api/v2/history/events`
- [x] `PUT /api/1/history/events` (Add a history event) ✅ Migrated to `POST /api/v2/history/events`
- [x] `PATCH /api/1/history/events` (Edit a history event) ✅ Migrated to `PUT /api/v2/history/events/{event_id}`
- [x] `DELETE /api/1/history/events` (Delete history events) ✅ Migrated to `DELETE /api/v2/history/events/{event_id}`
- [x] `GET /api/1/history/events/details` (Get details for a specific event) ✅ Migrated to `GET /api/v2/history/events/details`
- [ ] `POST /api/1/history/events/export` (Export history events to a file in a directory)
- [ ] `PUT /api/1/history/events/export` (Download history events as a CSV file)
- [ ] `GET /api/1/history/events/export/download` (Download an exported history events CSV)
- [x] `GET /api/1/history/actionable_items` (Get missing prices/acquisitions for accounting) ✅ Migrated to `GET /api/v2/history/actionable_items`
- [ ] `GET /api/1/history/skipped_external_events` (Get summary of skipped events)
- [ ] `PUT /api/1/history/skipped_external_events` (Export skipped events to a file in a directory)
- [ ] `PATCH /api/1/history/skipped_external_events` (Download skipped events as a CSV)
- [ ] `POST /api/1/history/skipped_external_events` (Reprocess skipped events)
- [x] `GET /api/1/history/events/type_mappings` (Get mappings of event types) ✅ Migrated to `GET /api/v2/history/events/type_mappings`
- [x] `GET /api/1/history/events/counterparties` (Get details for all EVM counterparties) ✅ Migrated to `GET /api/v2/history/events/counterparties`
- [x] `GET /api/1/history/events/products` (Get products for all EVM counterparties) ✅ Migrated to `GET /api/v2/history/events/products`
- [x] `GET /api/1/reports` (Get a list of all PnL reports) ✅ Migrated to `GET /api/v2/reports/`
- [x] `GET /api/1/reports/<int:report_id>` (Get a specific PnL report) ✅ Migrated to `GET /api/v2/reports/{report_id}`
- [x] `DELETE /api/1/reports/<int:report_id>` (Delete a PnL report) ✅ Migrated to `DELETE /api/v2/reports/{report_id}`
- [x] `POST /api/1/reports/<int:report_id>/data` (Get data for a specific PnL report) ✅ Migrated to `GET /api/v2/reports/{report_id}/data`
- [ ] `POST /api/1/accounting/rules` (Query accounting rules)
- [ ] `PUT /api/1/accounting/rules` (Add an accounting rule)
- [ ] `PATCH /api/1/accounting/rules` (Edit an accounting rule)
- [ ] `DELETE /api/1/accounting/rules` (Delete an accounting rule)
- [ ] `GET /api/1/accounting/rules/info` (Get info on linkable accounting rule properties)
- [ ] `POST /api/1/accounting/rules/import` (Import accounting rules via file upload)
- [ ] `PUT /api/1/accounting/rules/import` (Import accounting rules via file path)
- [ ] `POST /api/1/accounting/rules/export` (Export accounting rules)
- [ ] `POST /api/1/accounting/rules/conflicts` (List accounting rule conflicts)
- [ ] `PATCH /api/1/accounting/rules/conflicts` (Solve accounting rule conflicts)
- [ ] `POST /api/1/balances/historical` (Get historical balance for all assets at a timestamp)
- [ ] `POST /api/1/balances/historical/asset` (Get historical amounts for a single asset)
- [ ] `POST /api/1/balances/historical/netvalue` (Get historical net value)

#### **Ignored Assets & Actions**

- [x] `GET /api/1/assets/ignored` (Get all ignored assets) ✅ Migrated to `GET /api/v2/assets/ignored`
- [x] `PUT /api/1/assets/ignored` (Add assets to ignored list) ✅ Migrated to `POST /api/v2/assets/ignored` with action='add'
- [x] `DELETE /api/1/assets/ignored` (Remove assets from ignored list) ✅ Migrated to `POST /api/v2/assets/ignored` with action='remove'
- [ ] `POST /api/1/assets/ignored/whitelist` (Add a spam token to the false positive list)
- [ ] `DELETE /api/1/assets/ignored/whitelist` (Remove a token from the false positive list)
- [ ] `GET /api/1/assets/ignored/whitelist` (Get the list of false positive spam tokens)
- [ ] `POST /api/1/assets/evm/spam/` (Mark EVM tokens as spam)
- [ ] `DELETE /api/1/assets/evm/spam/` (Unmark an EVM token as spam)
- [ ] `PUT /api/1/actions/ignored` (Add action IDs to ignored list)
- [ ] `DELETE /api/1/actions/ignored` (Remove action IDs from ignored list)

#### **DeFi Modules**

- [ ] `DELETE /api/1/blockchains/eth/modules/data` (Purge all DeFi module data)
- [ ] `DELETE /api/1/blockchains/eth/modules/<string:module_name>/data` (Purge data for a specific DeFi module)
- [ ] `GET /api/1/blockchains/eth/modules` (Get list of supported DeFi modules)
- [ ] `GET /api/1/blockchains/eth/modules/liquity/balances` (Get Liquity trove positions)
- [ ] `GET /api/1/blockchains/eth/modules/liquity/staking` (Get Liquity staking positions)
- [ ] `GET /api/1/blockchains/eth/modules/liquity/pool` (Get Liquity stability pool positions)
- [ ] `GET /api/1/blockchains/eth/modules/<string:module>/balances` (Get module balances)
- [ ] `GET /api/1/blockchains/eth/modules/<string:module>/v<string:version>/balances` (Get versioned module balances)
- [ ] `GET /api/1/blockchains/eth/modules/<string:module>/stats` (Get module statistics)
- [ ] `GET /api/1/blockchains/eth/modules/pickle/dill` (Get Pickle DILL balance)
- [ ] `GET /api/1/blockchains/eth/modules/loopring/balances` (Get Loopring balances)
- [ ] `GET /api/1/airdrops/metadata` (Get airdrops metadata)
- [ ] `GET /api/1/defi/metadata` (Get DeFi protocols metadata)
- [ ] `POST /api/1/protocols/data/refresh` (Refresh data for a DeFi protocol cache)
- [ ] `GET /api/1/protocols/data/refresh` (Get a list of protocols with refreshable cache)

#### **Names, Addresses & Avatars**

- [ ] `GET /api/1/queried_addresses` (Get all queried addresses per module)
- [ ] `PUT /api/1/queried_addresses` (Add a queried address for a module)
- [ ] `DELETE /api/1/queried_addresses` (Remove a queried address for a module)
- [x] `POST /api/1/names` (Search for names across all sources) ✅ Migrated to `POST /api/v2/names/`
- [x] `POST /api/1/names/ens/reverse` (Reverse lookup ENS names for addresses) ✅ Migrated to `POST /api/v2/names/ens/reverse`
- [x] `POST /api/1/names/ens/resolve` (Resolve an ENS name to an address) ✅ Migrated to `POST /api/v2/names/ens/resolve`
- [x] `GET /api/1/avatars/ens/<string:ens_name>` (Get an ENS avatar) ✅ Migrated to `GET /api/v2/names/avatars/ens/{ens_name}`
- [x] `POST /api/1/names/addressbook/<string:book_type>` (Get address book entries) ✅ Migrated to `POST /api/v2/names/addressbook/{book_type}`
- [x] `PUT /api/1/names/addressbook/<string:book_type>` (Add address book entries) ✅ Migrated to `PUT /api/v2/names/addressbook/{book_type}`
- [x] `PATCH /api/1/names/addressbook/<string:book_type>` (Update address book entries) ✅ Migrated to `PATCH /api/v2/names/addressbook/{book_type}`
- [x] `DELETE /api/1/names/addressbook/<string:book_type>` (Delete address book entries) ✅ Migrated to `DELETE /api/v2/names/addressbook/{book_type}`

#### **Data Import/Export & DB Management**

- [x] `GET /api/1/database/info` (Get database info) ✅ Migrated to `GET /api/v2/data/database/info`
- [x] `GET /api/1/database/backups` (Download a DB backup) ✅ Migrated to `GET /api/v2/data/database/backups`
- [x] `PUT /api/1/database/backups` (Create a DB backup) ✅ Migrated to `POST /api/v2/data/database/backup`
- [ ] `DELETE /api/1/database/backups` (Delete DB backups)
- [x] `POST /api/1/import` (Import data from a file upload) ✅ Migrated to `POST /api/v2/data/import`
- [x] `PUT /api/1/import` (Import data from a file path) ✅ Migrated to `POST /api/v2/data/import`
- [ ] `GET /api/1/snapshots/<int:timestamp>` (Get a DB snapshot)
- [ ] `PUT /api/1/snapshots` (Import a DB snapshot via file paths)
- [ ] `POST /api/1/snapshots` (Import a DB snapshot via file upload)
- [ ] `PATCH /api/1/snapshots/<int:timestamp>` (Edit a DB snapshot)
- [ ] `DELETE /api/1/snapshots/<int:timestamp>` (Delete a DB snapshot)

#### **Miscellaneous**

- [x] `GET /api/1/ping` (Ping the server) ✅ Migrated to `GET /api/v2/info/ping`
- [x] `GET /api/1/info` (Get application info) ✅ Migrated to `GET /api/v2/info/info`
- [x] `GET /api/1/watchers` (Get premium watchers) ✅ Migrated to `GET /api/v2/watchers/`
- [x] `PUT /api/1/watchers` (Add premium watchers) ✅ Migrated to `PUT /api/v2/watchers/`
- [x] `PATCH /api/1/watchers` (Edit premium watchers) ✅ Migrated to `PATCH /api/v2/watchers/`
- [x] `DELETE /api/1/watchers` (Delete premium watchers) ✅ Migrated to `DELETE /api/v2/watchers/`
- [x] `POST /api/1/cache/<string:cache_type>/clear` (Clear icon or avatar cache) ✅ Migrated to `POST /api/v2/cache/{cache_type}/clear`
- [x] `POST /api/1/wallet/transfer/token` (Prepare a token transfer) ✅ Migrated to `POST /api/v2/wallet/transfer/token`
- [x] `POST /api/1/wallet/transfer/native` (Prepare a native asset transfer) ✅ Migrated to `POST /api/v2/wallet/transfer/native`
- [x] `POST /api/1/wallet/interacted` (Check if two addresses have interacted) ✅ Migrated to `POST /api/v2/wallet/interacted`
- [x] `POST /api/1/wallet/balance` (Fetch token balance for an address) ✅ Migrated to `POST /api/v2/wallet/balance`
- [x] `POST /api/1/calendar` (Query calendar events) ✅ Migrated to `POST /api/v2/calendar/`
- [x] `PUT /api/1/calendar` (Create a calendar entry) ✅ Migrated to `PUT /api/v2/calendar/`
- [x] `DELETE /api/1/calendar` (Delete a calendar entry) ✅ Migrated to `DELETE /api/v2/calendar/`
- [x] `PATCH /api/1/calendar` (Update a calendar entry) ✅ Migrated to `PATCH /api/v2/calendar/`
- [x] `POST /api/1/calendar/reminders` (Query calendar reminders for an event) ✅ Migrated to `POST /api/v2/calendar/reminders`
- [x] `PUT /api/1/calendar/reminders` (Create calendar reminders) ✅ Migrated to `PUT /api/v2/calendar/reminders`
- [x] `DELETE /api/1/calendar/reminders` (Delete a calendar reminder) ✅ Migrated to `DELETE /api/v2/calendar/reminders`
- [x] `PATCH /api/1/calendar/reminders` (Update a calendar reminder) ✅ Migrated to `PATCH /api/v2/calendar/reminders`
