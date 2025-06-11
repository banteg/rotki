# ORM Integration Guide

This guide shows how to integrate the new ORM system into the existing Rotkehlchen codebase.

## Architecture Overview

The ORM migration follows these principles:
1. **Repository Pattern**: Each domain has its own repository for data access
2. **Unit of Work**: Transactions are managed explicitly for data consistency
3. **Type Safety**: Full SQLAlchemy 2.0 type hints throughout
4. **No Compatibility Layers**: Direct 1:1 migration as requested

## Component Structure

```
rotkehlchen/
├── db/orm/
│   ├── models.py              # SQLAlchemy models
│   ├── database.py            # Database initialization
│   ├── repositories/          # Repository implementations
│   │   ├── base.py           # Base repository class
│   │   ├── accounts.py       # Blockchain accounts
│   │   ├── settings.py       # Application settings
│   │   └── ...               # Other repositories
│   └── session.py            # Session management
├── rotkehlchen_orm.py        # Main app using ORM
├── accounting/
│   └── accountant_orm.py     # Accounting with ORM
├── api/
│   └── rest_orm.py          # REST API with ORM
└── ...
```

## Migration Steps

### 1. Database Initialization

Replace old DBHandler initialization:

```python
# Old way
from rotkehlchen.db.dbhandler import DBHandler
db = DBHandler(user_data_dir, password, msg_aggregator)

# New way
from rotkehlchen.db.orm.database import create_database
db = create_database(user_data_dir, password)
```

### 2. Settings Management

```python
# Old way
with db.conn.read_ctx() as cursor:
    settings = db.get_settings(cursor)

# New way
settings = db.repos.settings.get_all_settings()
```

### 3. Account Management

```python
# Old way
with db.user_write() as cursor:
    db.add_blockchain_accounts(cursor, blockchain, accounts)

# New way
with db.repos.unit_of_work():
    for account in accounts:
        db.repos.accounts.add_account(blockchain, account)
```

### 4. Transaction Management

The new system uses explicit transaction management:

```python
# Read operations (no transaction needed)
accounts = db.repos.accounts.get_all_accounts()

# Write operations (transaction required)
with db.repos.unit_of_work():
    db.repos.accounts.add_account(...)
    db.repos.tags.add_tag(...)
    # All changes committed atomically
```

### 5. Complex Queries

For complex queries, extend the repository:

```python
class AccountRepository(BaseRepository[BlockchainAccount]):
    def get_accounts_with_balance(self, min_balance: FVal):
        stmt = select(BlockchainAccount).join(
            BalanceSnapshot
        ).filter(
            BalanceSnapshot.amount >= min_balance
        )
        return list(self.session.execute(stmt).scalars().all())
```

## Integration Points

### 1. API Layer

The REST API uses repositories directly:

```python
class RestAPI:
    def get_accounts(self):
        db = self._get_db()
        accounts = db.repos.accounts.get_all_accounts()
        return self._make_response(accounts)
```

### 2. Accounting Module

The accountant uses ORM for event processing:

```python
class Accountant:
    def process_history(self, start_ts, end_ts):
        events = self.db.repos.history_events.get_events(
            from_timestamp=start_ts,
            to_timestamp=end_ts,
        )
        # Process events...
```

### 3. Exchange Management

Exchanges store credentials in the database:

```python
class ExchangeManager:
    def setup_exchange(self, name, location, credentials):
        with self.db.repos.unit_of_work():
            self.db.repos.credentials.add_credential(
                name=name,
                location=location,
                **credentials
            )
```

## Testing

### Unit Tests

Use in-memory SQLite for fast tests:

```python
def test_account_repository():
    db = create_test_database()
    
    with db.repos.unit_of_work():
        db.repos.accounts.add_account('ethereum', '0x123...')
    
    accounts = db.repos.accounts.get_all_accounts()
    assert len(accounts) == 1
```

### Integration Tests

Test complete workflows:

```python
def test_accounting_workflow():
    db = create_test_database()
    accountant = Accountant(db, ...)
    
    # Add test data
    with db.repos.unit_of_work():
        db.repos.history_events.add_event(...)
    
    # Process accounting
    report = accountant.process_history(start_ts, end_ts)
    assert report.processed_events > 0
```

## Performance Considerations

1. **Eager Loading**: Use `joinedload` for related data:
   ```python
   stmt = select(Account).options(joinedload(Account.tags))
   ```

2. **Bulk Operations**: Use bulk methods for large datasets:
   ```python
   db.repos.accounts.bulk_insert(accounts_list)
   ```

3. **Query Optimization**: Add indexes in models:
   ```python
   class HistoryEvent(Base):
       __table_args__ = (
           Index('idx_timestamp', 'timestamp'),
           Index('idx_location_timestamp', 'location', 'timestamp'),
       )
   ```

## Common Patterns

### 1. Filtering and Pagination

```python
def get_events_paginated(page: int, limit: int):
    offset = (page - 1) * limit
    return db.repos.history_events.get_events(
        limit=limit,
        offset=offset,
        order_by='timestamp',
        order_ascending=False,
    )
```

### 2. Aggregations

```python
def get_balance_totals():
    stmt = select(
        Asset.identifier,
        func.sum(Balance.amount).label('total')
    ).join(Balance).group_by(Asset.identifier)
    
    return self.session.execute(stmt).all()
```

### 3. Conditional Updates

```python
def update_if_changed(account_id: int, new_label: str):
    account = db.repos.accounts.get_account(account_id)
    if account and account.label != new_label:
        with db.repos.unit_of_work():
            db.repos.accounts.update_label(account_id, new_label)
```

## Troubleshooting

### Common Issues

1. **Session Errors**: Always use `unit_of_work()` for writes
2. **Import Errors**: Ensure all models are imported before use
3. **Type Errors**: Use proper type conversions (e.g., `FVal` to `str`)

### Debug Mode

Enable SQL logging for debugging:

```python
db = create_database(user_data_dir, password, echo_sql=True)
```

## Next Steps

1. Continue migrating remaining modules
2. Add performance benchmarks
3. Update all tests to use ORM
4. Remove old DBHandler once migration is complete

## Incomplete Areas (TODO)

The following still need ORM implementation:
- Premium sync functionality
- Data import/export
- Some chain-specific decoders
- Performance-critical queries may need optimization