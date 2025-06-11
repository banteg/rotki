# Database Architecture Analysis

## Current State - God Object Anti-Pattern

### DBHandler.py Analysis
- **3,569 lines of code**
- **153 methods** in a single class
- Handles ALL database operations for the user database

### Major Responsibilities (Too Many!)

1. **Connection Management**
   - Password handling, encryption/decryption
   - Connection lifecycle (connect/disconnect)
   - Backup/restore operations
   - Schema upgrades

2. **Settings Management** (~15 methods)
   - get_setting() with overloads for each type
   - set_setting()
   - get_settings(), set_settings()

3. **Cache Management** (~25 methods)
   - Static cache operations
   - Dynamic cache with 9 different overloads
   - Cache deletion

4. **Account Management** (~20 methods)
   - Blockchain accounts CRUD
   - Single blockchain addresses
   - Bitcoin xpub management
   - EVM account details

5. **Asset Operations** (~10 methods)
   - Asset identifiers
   - Owned assets
   - Asset value distribution
   - Asset replacement

6. **Balance Management** (~15 methods)
   - Manually tracked balances
   - Timed balances
   - Collection balances
   - Balance querying

7. **Trading/Exchange** (~10 methods)
   - Exchange credentials
   - Binance pairs
   - Margin positions
   - Used query ranges

8. **Tags Management** (~6 methods)
   - Tag CRUD operations
   - Tag mappings

9. **User Features** (~10 methods)
   - User notes
   - RPC nodes
   - External events

10. **Misc Operations** (~20 methods)
    - Premium credentials
    - Location data
    - Associated locations
    - Database info

### Code Smells

1. **Violation of Single Responsibility Principle**
   - One class doing everything
   - Mixed levels of abstraction
   - Business logic mixed with data access

2. **Poor Cohesion**
   - Methods grouped by database table, not by domain
   - No clear boundaries between features

3. **High Coupling**
   - Direct SQL everywhere
   - No abstraction layer
   - Hard to test individual features

4. **Transaction Management Issues**
   - Manual transaction handling
   - Context managers scattered throughout
   - No clear transaction boundaries

5. **Type Safety Issues**
   - Overloaded methods with Literal types
   - Manual type conversions
   - No domain models

## Proposed Repository Architecture

### Design Principles
1. **Domain-Driven Design** - Organize by business domain, not database tables
2. **Repository Pattern** - Abstract data access behind interfaces
3. **Unit of Work** - Manage transactions at business operation level
4. **CQRS Light** - Separate read models from write models where beneficial

### Proposed Structure

```
rotkehlchen/db/orm/
├── repositories/
│   ├── base.py                 # Base repository with common CRUD
│   ├── unit_of_work.py        # Transaction management
│   │
│   ├── accounts/              # Account management domain
│   │   ├── __init__.py
│   │   ├── blockchain_repository.py
│   │   ├── xpub_repository.py
│   │   └── account_service.py
│   │
│   ├── assets/                # Asset management domain
│   │   ├── __init__.py
│   │   ├── asset_repository.py
│   │   ├── owned_assets_repository.py
│   │   └── asset_service.py
│   │
│   ├── balances/              # Balance tracking domain
│   │   ├── __init__.py
│   │   ├── manual_balance_repository.py
│   │   ├── timed_balance_repository.py
│   │   └── balance_service.py
│   │
│   ├── trading/               # Trading domain
│   │   ├── __init__.py
│   │   ├── exchange_repository.py
│   │   ├── margin_repository.py
│   │   └── trading_service.py
│   │
│   ├── settings/              # Settings & configuration
│   │   ├── __init__.py
│   │   ├── settings_repository.py
│   │   ├── cache_repository.py
│   │   └── config_service.py
│   │
│   ├── history/               # Historical data domain
│   │   ├── __init__.py
│   │   ├── event_repository.py
│   │   ├── transaction_repository.py
│   │   └── history_service.py
│   │
│   └── user_features/         # User features
│       ├── __init__.py
│       ├── tag_repository.py
│       ├── note_repository.py
│       └── feature_service.py
```

### Key Improvements

1. **Separation of Concerns**
   - Each repository handles one aggregate root
   - Services coordinate between repositories
   - Clear domain boundaries

2. **Testability**
   - Mock repositories for unit tests
   - In-memory implementations possible
   - Test business logic without database

3. **Maintainability**
   - Find code by domain concept
   - Changes isolated to specific areas
   - Clear dependencies

4. **Transaction Management**
   - Unit of Work pattern for transactions
   - Automatic rollback on errors
   - Consistent transaction boundaries

5. **Type Safety**
   - Return domain models, not tuples
   - Strong typing throughout
   - No manual SQL string building

### Migration Strategy

1. **Phase 1**: Create base infrastructure
   - BaseRepository with common CRUD
   - UnitOfWork for transaction management
   - Start with one domain (e.g., Settings)

2. **Phase 2**: Migrate by domain
   - One repository at a time
   - Keep DBHandler as facade initially
   - Gradually move methods to repositories

3. **Phase 3**: Remove god object
   - Replace DBHandler usage with repositories
   - Remove empty DBHandler class
   - Clean up legacy code

### Example Repository Implementation

```python
class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
    
    def get(self, id: Any) -> Optional[T]:
        return self.session.query(self.model_class).get(id)
    
    def add(self, entity: T) -> T:
        self.session.add(entity)
        return entity
    
    def delete(self, entity: T) -> None:
        self.session.delete(entity)

class AccountRepository(BaseRepository[BlockchainAccount]):
    def get_by_blockchain(self, blockchain: str) -> list[BlockchainAccount]:
        return self.session.query(BlockchainAccount).filter_by(
            blockchain=blockchain
        ).all()
    
    def get_with_balances(self, address: str) -> Optional[AccountWithBalances]:
        # Complex query with joins
        pass
```

### Benefits

1. **80% reduction in class size** - From 3500+ lines to ~200 per repository
2. **Clear responsibility** - Each repository = one domain
3. **Easier onboarding** - New developers find code by domain
4. **Better testing** - Mock individual repositories
5. **Gradual migration** - Can be done incrementally