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

## Future Enhancements

1. Add remaining models (NFTs, Validators, etc.)
2. Implement Alembic for schema migrations
3. Add query builders for complex operations
4. Create ORM-based data access layer
5. Add comprehensive test coverage