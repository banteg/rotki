# SQLAlchemy ORM Implementation for Rotkehlchen

This directory contains the SQLAlchemy ORM implementation for migrating from raw SQL to a more maintainable ORM-based approach.

## Structure

- `base.py` - Core database setup with gevent compatibility and SQLCipher support
- `types.py` - Custom SQLAlchemy types for special columns (BLOB, FVal, etc.)
- `enums.py` - Enum table models (Location, AssetTypes, etc.)
- `models.py` - Core models (Settings, Assets, Tags, etc.)
- `transactions.py` - Transaction-related models
- `history_events.py` - History event models
- `migration.py` - Utilities for gradual migration from raw SQL
- `sqlcipher.py` - SQLCipher dialect configuration

## Key Features

### 1. Gevent Compatibility
- Uses `Semaphore` for thread safety
- Single connection with `StaticPool`
- Proper context managers for sessions

### 2. SQLCipher Support
- Encrypted database support via custom dialect
- Compatible with existing rotkehlchen encryption

### 3. Custom Types
- `HexBytesType` - Converts hex strings to BLOB
- `FValType` - Handles decimal values
- `TimestampType` - Integer timestamp handling
- `BooleanType` - SQLite boolean (0/1) support
- `CharEnumType` - CHAR(1) enum support

### 4. Migration Strategy

#### Phase 1: Foundation (Current)
✅ Base SQLAlchemy setup
✅ Custom types
✅ Enum models
✅ Core models (Settings, Assets, Tags)
✅ Transaction models
✅ History event models

#### Phase 2: Integration
- Compatibility layer with existing DBHandler
- Gradual query migration
- Dual support (ORM + raw SQL)

#### Phase 3: Full Migration
- Replace all raw SQL with ORM
- Remove old database handlers
- Use Alembic for migrations

## Usage Examples

### Basic Setup
```python
from rotkehlchen.db.orm import init_user_db, Settings

# Initialize database
db = init_user_db(db_path, password='your_password')

# Create tables
db.create_tables()

# Use ORM
with db.session() as session:
    setting = Settings(name='version', value='1.0.0')
    session.add(setting)
    session.commit()
```

### Gradual Migration
```python
from rotkehlchen.db.orm import ORMCompatibilityLayer

# Initialize compatibility layer
compat = ORMCompatibilityLayer()
compat.init_from_dbhandler(existing_db_handler)

# Use hybrid approach
value = compat.get_settings_hybrid('version')
```

### Query Examples
```python
# Simple query
with db.session() as session:
    settings = session.query(Settings).all()
    
# Filtered query
with db.session() as session:
    eth_assets = session.query(Asset).filter(
        Asset.identifier.like('ETH%')
    ).all()
    
# Join query
with db.session() as session:
    balances = session.query(TimedBalance).join(
        Asset, TimedBalance.currency == Asset.identifier
    ).filter(
        TimedBalance.timestamp > 1000000
    ).all()
```

## Migration Guidelines

1. **Start Small**: Begin with simple tables (Settings, Tags)
2. **Test Thoroughly**: Ensure ORM queries match raw SQL results
3. **Use Compatibility Layer**: Allow fallback to raw SQL
4. **Monitor Performance**: Profile critical queries
5. **Gradual Rollout**: Migrate one module at a time

## Performance Considerations

- Indexes are defined in models for optimal performance
- Bulk operations use `bulk_insert_mappings()` for efficiency
- Query optimization with eager loading where needed
- Connection pooling disabled for SQLCipher compatibility

## Database Relationships

### User Database
- **BlockchainAccount** → XpubMapping, EvmAccountDetails, NFT, Calendar
- **Asset** → TimedBalance, ManuallyTrackedBalance, MarginPosition, HistoryEvent
- **EvmTransaction** → EvmInternalTransaction, EvmTxReceipt, OptimismTransaction
- **HistoryEvent** → EvmEventInfo, EthStakingEventInfo, HistoryEventMapping
- **Eth2Validator** → EthValidatorsDataCache, Eth2DailyStakingDetails
- **PnlReport** → PnlReportTotal, PnlReportSetting, PnlEvent

### Global Database
- **GlobalAsset** → CommonAssetDetails, EvmToken, CustomAsset, AssetCollection
- **EvmToken** → UnderlyingTokensList
- **AssetCollection** → MultiassetMapping
- **ContractABI** → ContractData

## Alembic Migrations

### Setup
Alembic is configured for managing schema migrations:

```python
from rotkehlchen.db.orm.alembic_helper import AlembicHelper

# Initialize helper for user database
helper = AlembicHelper(
    db_type='user',
    db_path=Path('/path/to/rotkehlchen.db'),
    password='your_password'
)

# Create initial migration
helper.init_db()

# Create new migration
helper.create_migration("Add new feature")

# Upgrade to latest
helper.upgrade()
```

### Migration Commands
- `alembic revision --autogenerate -m "message"` - Create new migration
- `alembic upgrade head` - Upgrade to latest
- `alembic downgrade -1` - Rollback one migration
- `alembic current` - Show current revision
- `alembic history` - Show migration history

## Complete Model List

### User Database Models (50+ tables)
- Core: Settings, Asset, Tag, BlockchainAccount
- Credentials: UserCredentials, ExternalServiceCredentials
- Balances: TimedBalance, ManuallyTrackedBalance
- Transactions: EvmTransaction, EvmInternalTransaction, ZkSyncLiteTransaction
- Events: HistoryEvent, EvmEventInfo, EthStakingEventInfo
- ETH2: Eth2Validator, EthValidatorsDataCache
- DeFi: MarginPosition, CowswapOrder, GnosisPayData
- User Features: AddressBook, UserNote, Calendar, AccountingRule
- NFTs: NFT
- Infrastructure: RPCNode, ENSMapping, KeyValueCache

### Global Database Models
- Assets: GlobalAsset, CommonAssetDetails, EvmToken, CustomAsset
- Collections: AssetCollection, MultiassetMapping
- Pricing: PriceHistory, BinancePair
- Mappings: LocationAssetMapping, CounterpartyAssetMapping
- Infrastructure: ContractABI, DefaultRPCNode, Cache tables

### Transient Database Models
- PnlReport, PnlReportTotal, PnlReportSetting, PnlEvent
- TransientSettings

## Next Steps

1. Run tests to ensure ORM queries match raw SQL results
2. Migrate data access layer to use ORM
3. Create initial Alembic migration from existing schema
4. Implement query optimization for complex operations
5. Add comprehensive test coverage for all models