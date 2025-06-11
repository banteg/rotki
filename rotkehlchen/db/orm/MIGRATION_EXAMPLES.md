# ORM Migration Examples

This document provides complete examples of migrating from DBHandler to ORM.

## Example 1: Settings Management

### Old Code (DBHandler)
```python
# In some API endpoint or service
with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
    settings = self.rotkehlchen.data.db.get_settings(cursor)
    frontend_settings = self.rotkehlchen.data.db.get_setting(cursor, 'frontend_settings')

with self.rotkehlchen.data.db.user_write() as write_cursor:
    self.rotkehlchen.data.db.set_setting(write_cursor, 'frontend_settings', json.dumps(data))
```

### New Code (ORM)
```python
# In some API endpoint or service
db = self.rotkehlchen.data.db

# Read operations
settings = db.repos.settings.get_all_settings()
frontend_settings = db.repos.settings.get_setting('frontend_settings')

# Write operations with transaction
with db.repos.unit_of_work():
    db.repos.settings.set_setting('frontend_settings', json.dumps(data))
```

## Example 2: Blockchain Accounts

### Old Code (DBHandler)
```python
# Getting accounts
with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
    accounts = self.rotkehlchen.data.db.get_blockchain_accounts(cursor)

# Adding accounts
with self.rotkehlchen.data.db.user_write() as write_cursor:
    self.rotkehlchen.data.db.add_blockchain_accounts(
        write_cursor,
        blockchain=SupportedBlockchain.ETHEREUM,
        accounts=['0x123...', '0x456...'],
    )

# With tags
with self.rotkehlchen.data.db.user_write() as write_cursor:
    self.rotkehlchen.data.db.add_blockchain_accounts(
        write_cursor,
        blockchain=SupportedBlockchain.ETHEREUM,
        accounts=['0x789...'],
    )
    self.rotkehlchen.data.db.add_tag_mappings(
        write_cursor,
        tag_name='defi',
        accounts=['0x789...'],
    )
```

### New Code (ORM)
```python
db = self.rotkehlchen.data.db

# Getting accounts
all_accounts = db.repos.accounts.get_all_accounts()
eth_accounts = db.repos.accounts.get_accounts_by_blockchain('ethereum')

# Adding accounts with transaction
with db.repos.unit_of_work():
    for address in ['0x123...', '0x456...']:
        db.repos.accounts.add_account(
            blockchain='ethereum',
            address=address,
        )

# With tags
with db.repos.unit_of_work():
    db.repos.accounts.add_account(
        blockchain='ethereum',
        address='0x789...',
    )
    db.repos.tags.add_tag_mapping('defi', '0x789...', 'ethereum')
```

## Example 3: Exchange Management

### Old Code (DBHandler)
```python
# Getting exchange credentials
with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
    credentials = self.rotkehlchen.data.db.get_exchange_credentials(cursor)

# Adding exchange
with self.rotkehlchen.data.db.user_write() as write_cursor:
    self.rotkehlchen.data.db.add_exchange(
        write_cursor,
        location=Location.BINANCE,
        name='my_binance',
        api_key='key',
        api_secret='secret',
    )
```

### New Code (ORM)
```python
db = self.rotkehlchen.data.db

# Getting exchange credentials
all_credentials = db.repos.credentials.get_all_credentials()
binance_creds = db.repos.credentials.get_credentials_for_location(Location.BINANCE)

# Adding exchange
with db.repos.unit_of_work():
    db.repos.credentials.add_credential(
        name='my_binance',
        location='B',  # Location.BINANCE.serialize_for_db()
        api_key='key',
        api_secret='secret',
    )
```

## Example 4: History Events

### Old Code (DBHandler)
```python
# Query history events
with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
    events = self.rotkehlchen.data.db.get_history_events(
        cursor,
        from_timestamp=from_ts,
        to_timestamp=to_ts,
        event_types=[HistoryEventType.TRADE],
    )

# Add history event
with self.rotkehlchen.data.db.user_write() as write_cursor:
    self.rotkehlchen.data.db.add_history_event(
        write_cursor,
        event=history_event,
    )
```

### New Code (ORM)
```python
db = self.rotkehlchen.data.db

# Query history events
events = db.repos.history_events.get_events(
    from_timestamp=from_ts,
    to_timestamp=to_ts,
    event_types=['trade'],
)

# Add history event
with db.repos.unit_of_work():
    db.repos.history_events.add_event(history_event)
```

## Example 5: Complex Transaction

### Old Code (DBHandler)
```python
# Multiple operations in transaction
with self.rotkehlchen.data.db.user_write() as write_cursor:
    # Add account
    self.rotkehlchen.data.db.add_blockchain_accounts(
        write_cursor,
        blockchain=SupportedBlockchain.ETHEREUM,
        accounts=['0xabc...'],
    )
    
    # Create tag
    self.rotkehlchen.data.db.add_tag(
        write_cursor,
        name='yield',
        description='Yield farming',
        background_color='00FF00',
        foreground_color='000000',
    )
    
    # Tag the account
    self.rotkehlchen.data.db.add_tag_mappings(
        write_cursor,
        tag_name='yield',
        accounts=['0xabc...'],
    )
    
    # Update settings
    self.rotkehlchen.data.db.set_setting(
        write_cursor,
        'last_balance_save',
        str(ts_now()),
    )
```

### New Code (ORM)
```python
db = self.rotkehlchen.data.db

# Multiple operations in transaction
with db.repos.unit_of_work():
    # Add account
    db.repos.accounts.add_account(
        blockchain='ethereum',
        address='0xabc...',
    )
    
    # Create tag
    db.repos.tags.add_tag(
        name='yield',
        description='Yield farming',
        background_color='00FF00',
        foreground_color='000000',
    )
    
    # Tag the account
    db.repos.tags.add_tag_mapping('yield', '0xabc...', 'ethereum')
    
    # Update settings
    db.repos.settings.set_setting('last_balance_save', str(ts_now()))
```

## Example 6: Error Handling

### Old Code (DBHandler)
```python
try:
    with self.rotkehlchen.data.db.user_write() as write_cursor:
        self.rotkehlchen.data.db.add_tag(
            write_cursor,
            name='duplicate',
            description='This will fail',
            background_color='FFFFFF',
            foreground_color='000000',
        )
except sqlcipher.IntegrityError:
    raise InputError('Tag already exists')
```

### New Code (ORM)
```python
from sqlalchemy.exc import IntegrityError

try:
    with db.repos.unit_of_work():
        db.repos.tags.add_tag(
            name='duplicate',
            description='This will fail',
            background_color='FFFFFF',
            foreground_color='000000',
        )
except IntegrityError:
    raise InputError('Tag already exists')
```

## Example 7: Querying with Filters

### Old Code (DBHandler)
```python
# Complex query with filters
with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
    cursor.execute(
        'SELECT * FROM blockchain_accounts WHERE blockchain = ? AND label LIKE ?',
        ('ethereum', '%defi%'),
    )
    accounts = cursor.fetchall()
```

### New Code (ORM)
```python
# Using repository methods
eth_accounts = db.repos.accounts.get_accounts_by_blockchain('ethereum')
defi_accounts = [acc for acc in eth_accounts if acc.label and 'defi' in acc.label.lower()]

# Or implement a custom repository method
class BlockchainAccountRepository(BaseRepository[BlockchainAccount]):
    def search_by_label(self, blockchain: str, search_term: str) -> list[BlockchainAccount]:
        stmt = select(BlockchainAccount).filter(
            and_(
                BlockchainAccount.blockchain == blockchain,
                BlockchainAccount.label.like(f'%{search_term}%'),
            )
        )
        return list(self.session.execute(stmt).scalars().all())
```

## Migration Checklist

When migrating a module:

1. **Identify all DBHandler usages**
   ```bash
   grep -r "data.db\." path/to/module/
   grep -r "conn.read_ctx\|user_write" path/to/module/
   ```

2. **Map operations to repositories**
   - `get_settings()` → `repos.settings.get_all_settings()`
   - `add_blockchain_accounts()` → `repos.accounts.add_account()`
   - `get_history_events()` → `repos.history_events.get_events()`
   - etc.

3. **Update transaction handling**
   - Replace `with conn.read_ctx()` with direct repository calls
   - Replace `with user_write()` with `with repos.unit_of_work()`

4. **Update error handling**
   - Replace `sqlcipher.IntegrityError` with `sqlalchemy.exc.IntegrityError`
   - Update other database-specific exceptions

5. **Test thoroughly**
   - Unit tests with test repositories
   - Integration tests with real database
   - Performance comparison

6. **Mark incomplete parts with TODO**
   ```python
   # TODO: Implement custom query for performance
   # TODO: Add pagination support
   # TODO: Handle edge case for...
   ```