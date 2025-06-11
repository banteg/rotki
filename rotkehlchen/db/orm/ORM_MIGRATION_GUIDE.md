# ORM Migration Guide

This guide helps developers migrate from the old `DBHandler` to the new ORM-based architecture.

## Quick Start

### 1. Replace DBHandler Import

**Old:**
```python
from rotkehlchen.db.dbhandler import DBHandler

db = DBHandler(user_data_dir, password, initial_settings)
```

**New (with adapter):**
```python
from rotkehlchen.db.orm.adapter import create_dbhandler_adapter

db = create_dbhandler_adapter(user_data_dir, password)
```

**New (direct ORM):**
```python
from rotkehlchen.db.orm.database import create_database

db = create_database(user_data_dir, password)
```

### 2. Common Operations Migration

#### Settings

**Old:**
```python
# Get setting
value = db.get_setting('frontend_settings')

# Set setting  
db.set_setting('frontend_settings', json.dumps(settings))

# Get all settings
settings = db.get_settings()
```

**New:**
```python
# Get setting
value = db.repos.settings.get_setting('frontend_settings')

# Set setting
db.repos.settings.set_setting('frontend_settings', json.dumps(settings))
db.session_manager.user_session.commit()

# Get all settings
settings = db.repos.settings.get_all_settings()
```

#### Blockchain Accounts

**Old:**
```python
# Add accounts
db.add_blockchain_accounts(
    blockchain=SupportedBlockchain.ETHEREUM,
    accounts=['0x123...', '0x456...'],
)

# Get accounts
accounts = db.get_blockchain_accounts()

# Remove accounts
db.remove_blockchain_accounts(
    blockchain=SupportedBlockchain.ETHEREUM,
    accounts=['0x123...'],
)
```

**New:**
```python
# Add accounts
for address in ['0x123...', '0x456...']:
    db.repos.accounts.add_account(
        blockchain='ethereum',
        address=address,
    )
db.session_manager.user_session.commit()

# Get accounts
accounts = db.repos.accounts.get_all_accounts()

# Remove accounts
db.repos.accounts.delete_account('ethereum', '0x123...')
db.session_manager.user_session.commit()
```

#### Tags

**Old:**
```python
# Add tag
db.add_tag(
    name='DeFi',
    description='DeFi protocols',
    background_color='55EE55',
    foreground_color='000000',
)

# Get tags
tags = db.get_tags()

# Tag account
db.add_tag_mapping(tag_name='DeFi', account='0x...', blockchain='ethereum')
```

**New:**
```python
# Add tag
db.repos.tags.add_tag(
    name='DeFi',
    description='DeFi protocols', 
    background_color='55EE55',
    foreground_color='000000',
)
db.session_manager.user_session.commit()

# Get tags
tags = db.repos.tags.get_all_tags()

# Tag account
db.repos.tags.add_tag_mapping('DeFi', '0x...', 'ethereum')
db.session_manager.user_session.commit()
```

#### Manual Balances

**Old:**
```python
# Add balance
balance_id = db.add_manual_balance(
    asset=A_ETH,
    label='Cold Storage',
    amount=FVal('10.5'),
    location=Location.BLOCKCHAIN,
    tags=['hodl'],
)

# Get balances
balances = db.get_manual_balances()

# Update balance
db.edit_manual_balance(
    balance_id=balance_id,
    amount=FVal('15.5'),
)
```

**New:**
```python
# Add balance
balance = db.repos.manual_balances.add_balance(
    asset='ETH',
    label='Cold Storage',
    amount='10.5',
    location='B',
    tags=['hodl'],
)
balance_id = balance.identifier
db.session_manager.user_session.commit()

# Get balances
balances = db.repos.manual_balances.get_all_balances()

# Update balance
db.repos.manual_balances.update_balance(
    identifier=balance_id,
    amount='15.5',
)
db.session_manager.user_session.commit()
```

### 3. Transaction Handling

#### Simple Operations

**Old:**
```python
# Implicit transaction per operation
db.set_setting('key1', 'value1')
db.set_setting('key2', 'value2')
```

**New:**
```python
# Explicit transaction control
with db.repos.unit_of_work() as uow:
    db.repos.settings.set_setting('key1', 'value1')
    db.repos.settings.set_setting('key2', 'value2')
    # Both committed together
```

#### Complex Operations

**Old:**
```python
# Manual transaction management
cursor = db.conn.cursor()
try:
    # Multiple operations
    cursor.execute("INSERT INTO ...")
    cursor.execute("UPDATE ...")
    db.conn.commit()
except Exception:
    db.conn.rollback()
    raise
```

**New:**
```python
# Automatic transaction management
with db.repos.unit_of_work() as uow:
    # Multiple operations
    db.repos.accounts.add_account(...)
    db.repos.tags.add_tag(...)
    db.repos.tags.add_tag_mapping(...)
    # All committed on success
    # All rolled back on exception
```

### 4. Query Patterns

#### Filtering

**Old:**
```python
# Raw SQL with parameters
cursor = db.conn.cursor()
cursor.execute(
    "SELECT * FROM history_events WHERE timestamp >= ? AND timestamp <= ?",
    (from_ts, to_ts)
)
events = cursor.fetchall()
```

**New:**
```python
# Repository methods with parameters
events = db.repos.history_events.get_events(
    from_timestamp=from_ts,
    to_timestamp=to_ts,
)
```

#### Aggregations

**Old:**
```python
# Manual aggregation
cursor.execute("SELECT COUNT(*) FROM blockchain_accounts WHERE blockchain = ?", ('ethereum',))
count = cursor.fetchone()[0]
```

**New:**
```python
# Repository aggregation methods
count = db.repos.accounts.get_account_count(blockchain='ethereum')
```

### 5. Error Handling

**Old:**
```python
from rotkehlchen.errors import DBUpgradeError, DeserializationError

try:
    db.add_blockchain_accounts(...)
except sqlcipher.IntegrityError as e:
    raise InputError(f"Account already exists: {e}")
```

**New:**
```python
from sqlalchemy.exc import IntegrityError
from rotkehlchen.errors.api import InputError

try:
    with db.repos.unit_of_work():
        db.repos.accounts.add_account(...)
except IntegrityError as e:
    raise InputError(f"Account already exists: {e}")
```

## Migration Strategy

### Phase 1: Adapter Usage
1. Replace `DBHandler` with `DBHandlerAdapter`
2. No code changes required
3. Test thoroughly

### Phase 2: Gradual Repository Adoption
1. Identify isolated modules
2. Replace adapter calls with direct repository usage
3. Add proper transaction management
4. Test each module

### Phase 3: Complete Migration
1. Remove all adapter usage
2. Delete old `DBHandler` code
3. Optimize repository methods
4. Add missing functionality

## Common Pitfalls

1. **Forgetting to commit** - ORM requires explicit commits
2. **N+1 queries** - Use eager loading for relationships
3. **Large result sets** - Use pagination and limits
4. **Transaction scope** - Keep transactions small
5. **Connection leaks** - Always use context managers

## Performance Tips

1. **Batch operations**
   ```python
   # Instead of multiple individual adds
   accounts = [
       db.repos.accounts.create_account_object(blockchain, address)
       for address in addresses  
   ]
   db.session_manager.user_session.bulk_save_objects(accounts)
   ```

2. **Use indexes**
   ```python
   # Indexes are defined in models
   # Queries automatically use them
   ```

3. **Limit results**
   ```python
   # Always use limit/offset for large datasets
   events = db.repos.history_events.get_events(
       limit=100,
       offset=0,
   )
   ```

## Testing Your Migration

1. **Unit Tests**
   ```python
   def test_migration(test_repos):
       # Use test fixtures
       test_repos.settings.set_setting('test', 'value')
       assert test_repos.settings.get_setting('test') == 'value'
   ```

2. **Integration Tests**
   ```python
   def test_with_real_db(orm_database):
       # Test with real database
       orm_database.repos.accounts.add_account(...)
       orm_database.session_manager.user_session.commit()
   ```

3. **Performance Tests**
   ```python
   # Compare old vs new implementation
   # Ensure no performance regression
   ```

## Getting Help

- Check the architecture documentation in `README.md`
- Look at test examples in `tests/unit/db/orm/`
- Review repository implementations in `repositories/`
- Ask in development channels for specific cases