# V1 to V2 API Resource Migration Mapping

This document lists all v1 API resource classes that need to be migrated to v2, based on the untracked v2 files found.

## Resources Found in V1 API

### 1. **Actions (IgnoredActionsResource)**
- **V1 Class**: `IgnoredActionsResource`
- **V1 Endpoint**: `/actions/ignored`
- **Methods**: GET, PUT, DELETE
- **Purpose**: Manages ignored action IDs

### 2. **Airdrops (EthereumAirdropsResource)**
- **V1 Class**: `EthereumAirdropsResource`
- **V1 Endpoint**: `/blockchains/eth/airdrops`
- **Methods**: GET
- **Purpose**: Retrieves Ethereum airdrop information

### 3. **Cache (ClearCacheResource)**
- **V1 Class**: `ClearCacheResource`
- **V1 Endpoint**: `/cache/<string:cache_type>/clear`
- **Methods**: POST
- **Purpose**: Clears various types of caches (icons, avatars)

### 4. **Calendar (CalendarResource, CalendarRemindersResource)**
- **V1 Class**: `CalendarResource`
- **V1 Endpoint**: `/calendar`
- **Methods**: GET, POST, PUT, DELETE
- **Purpose**: Manages calendar entries
- **V1 Class**: `CalendarRemindersResource`
- **V1 Endpoint**: `/calendar/reminders`
- **Methods**: GET, POST, DELETE
- **Purpose**: Manages calendar reminders

### 5. **Exchange Rates (ExchangeRatesResource)**
- **V1 Class**: `ExchangeRatesResource`
- **V1 Endpoint**: `/exchange_rates`
- **Methods**: GET
- **Purpose**: Retrieves exchange rates for currencies

### 6. **External Services (ExternalServicesResource)**
- **V1 Class**: `ExternalServicesResource`
- **V1 Endpoint**: `/external_services`
- **Methods**: GET, PUT, DELETE
- **Purpose**: Manages external service API credentials

### 7. **Import/Export**
- **V1 Class**: `DataImportResource`
- **V1 Endpoint**: `/import`
- **Methods**: PUT, POST
- **Purpose**: Imports data from various sources
- **V1 Class**: `ExportHistoryEventResource`
- **V1 Endpoint**: `/history/export`
- **Methods**: GET
- **Purpose**: Exports history events
- **V1 Class**: `ExportHistoryDownloadResource`
- **V1 Endpoint**: `/history/download`
- **Methods**: GET
- **Purpose**: Downloads exported history
- **V1 Class**: `AccountingRulesImportResource`
- **V1 Endpoint**: `/accounting/rules/import`
- **Methods**: PUT
- **Purpose**: Imports accounting rules
- **V1 Class**: `AccountingRulesExportResource`
- **V1 Endpoint**: `/accounting/rules/export`
- **Methods**: GET
- **Purpose**: Exports accounting rules

### 8. **Oracles (OraclesResource, NamedOracleCacheResource)**
- **V1 Class**: `OraclesResource`
- **V1 Endpoint**: `/oracles`
- **Methods**: GET
- **Purpose**: Gets supported oracles
- **V1 Class**: `NamedOracleCacheResource`
- **V1 Endpoint**: `/oracles/<string:oracle>/<string:item>`
- **Methods**: GET, POST, DELETE
- **Purpose**: Manages oracle cache

### 9. **Periodic (PeriodicDataResource)**
- **V1 Class**: `PeriodicDataResource`
- **V1 Endpoint**: `/periodic`
- **Methods**: GET
- **Purpose**: Queries periodic data

### 10. **Premium (UserPremiumKeyResource, UserPremiumSyncResource)**
- **V1 Class**: `UserPremiumKeyResource`
- **V1 Endpoint**: `/premium`
- **Methods**: DELETE
- **Purpose**: Manages premium key
- **V1 Class**: `UserPremiumSyncResource`
- **V1 Endpoint**: `/premium/sync`
- **Methods**: PUT
- **Purpose**: Syncs premium data

### 11. **Protocols (ProtocolDataRefreshResource)**
- **V1 Class**: `ProtocolDataRefreshResource`
- **V1 Endpoint**: `/protocols/data/refresh`
- **Methods**: GET, POST
- **Purpose**: Refreshes protocol data cache

### 12. **Queried Addresses (QueriedAddressesResource)**
- **V1 Class**: `QueriedAddressesResource`
- **V1 Endpoint**: `/queried_addresses`
- **Methods**: GET, PUT, DELETE
- **Purpose**: Manages addresses queried per module

### 13. **Snapshots (DBSnapshotsResource)**
- **V1 Class**: `DBSnapshotsResource`
- **V1 Endpoint**: `/snapshots`
- **Methods**: GET, POST, PATCH, DELETE
- **Purpose**: Manages database snapshots

### 14. **Staking (StakingResource)**
- **V1 Class**: `StakingResource`
- **V1 Endpoint**: `/staking/kraken`
- **Methods**: POST
- **Purpose**: Queries Kraken staking events

### 15. **Wallet Resources**
- **V1 Class**: `PrepareTokenTransferResource`
- **V1 Endpoint**: `/wallet/transfer/token`
- **Methods**: POST
- **Purpose**: Prepares token transfers
- **V1 Class**: `PrepareNativeTransferResource`
- **V1 Endpoint**: `/wallet/transfer/native`
- **Methods**: POST
- **Purpose**: Prepares native asset transfers
- **V1 Class**: `AddressesInteractedResource`
- **V1 Endpoint**: `/wallet/interacted`
- **Methods**: POST
- **Purpose**: Checks if addresses have interacted
- **V1 Class**: `AccountTokenBalanceResource`
- **V1 Endpoint**: `/wallet/balance`
- **Methods**: POST
- **Purpose**: Fetches token balance for address

## Additional Resources That May Need Migration

### History-Related Resources
- **V1 Class**: `HistoryActionableItemsResource`
- **V1 Endpoint**: `/history/actionable_items`
- **Methods**: GET
- **Purpose**: Gets actionable history items

### Other Staking Resources
- **V1 Class**: `Eth2StakingEventsResource`
- **V1 Endpoint**: `/blockchains/eth2/stake/events`
- **Methods**: GET, PUT, PATCH, DELETE
- **Purpose**: Manages ETH2 staking events

- **V1 Class**: `LiquityStakingResource`
- **V1 Endpoint**: `/blockchains/eth/modules/liquity/staking`
- **Methods**: GET, POST
- **Purpose**: Manages Liquity staking

## Summary

The v2 API already has router and service files for all these resources, but they need to be implemented with the actual business logic from v1. The migration should:

1. Move business logic from v1 resource methods to v2 service classes
2. Update v2 routers to use FastAPI decorators instead of Flask
3. Ensure all endpoints maintain backward compatibility
4. Use the new ORM models instead of raw SQL queries
5. Follow the established v2 patterns for dependency injection and error handling