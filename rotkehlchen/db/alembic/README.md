# Alembic Migration System for Rotkehlchen

This directory contains the Alembic migration system for the Rotkehlchen user database.

## Overview

We have successfully migrated the existing custom upgrade system to use Alembic for database migrations. This provides:

- Standard migration tooling
- Better support for rollbacks (downgrades)
- Automatic migration generation from SQLModel changes
- Integration with the existing rotkehlchen database system

## Structure

```
alembic/
├── env.py                    # Alembic environment configuration
├── script.py.mako           # Template for new migrations
├── versions/                # Migration files
│   ├── 001_initial_v48.py   # Initial migration representing v48 schema
│   ├── 026_v26_to_v27.py   # Ported upgrade from v26 to v27
│   ├── ...                  # Other ported migrations
│   └── 047_v47_to_v48.py   # Latest migration
├── create_initial_migration.py  # Script to generate initial migration
├── port_upgrades.py            # Script to port old upgrades
└── generate_initial_migration.py # Helper for migration generation
```

## Key Components

### AlembicManager (`db/alembic_manager.py`)

The `AlembicManager` class provides integration between Alembic and the existing rotkehlchen system:

- `transition_to_alembic()`: Transitions an existing database to use Alembic
- `run_migrations()`: Runs pending migrations
- `get_revision_for_db_version()`: Maps old version numbers to Alembic revisions

### Migration Files

Each migration file contains:
- `upgrade()`: Function to apply the migration
- `downgrade()`: Function to reverse the migration (where possible)

## Usage

### Transitioning an Existing Database

```python
from rotkehlchen.db.alembic_manager import AlembicManager

# Assuming db is a DBHandler instance
manager = AlembicManager(db)
manager.transition_to_alembic()
```

### Running Migrations

```python
manager.run_migrations()
```

### Creating a New Migration

```bash
# Auto-generate based on model changes
alembic revision --autogenerate -m "Add new feature"

# Or create an empty migration
alembic revision -m "Custom migration"
```

## Important Notes

1. **Only User Database**: This migration system only handles the user database. The global and transient databases have their own upgrade systems.

2. **Version Mapping**: The system maintains compatibility with the old version numbering:
   - v26 → `001_initial_v48` (base migration)
   - v27 → `026_v26_to_v27`
   - ...
   - v48 → `047_v47_to_v48`

3. **Encrypted Databases**: The system supports SQLCipher encrypted databases through environment variables:
   - `ROTKEHLCHEN_DB_PATH`: Path to the database file
   - `ROTKEHLCHEN_DB_PASSWORD`: Encryption password

4. **Downgrade Limitations**: Some migrations cannot be fully reversed due to data transformations. Downgrades are "best effort".

## Testing

Tests are located in:
- `tests/db/test_alembic_integration.py`: Integration tests for AlembicManager
- `tests/db/test_alembic_migrations.py`: Tests for individual migrations

Run tests with:
```bash
pytest tests/db/test_alembic_integration.py -v
```

## Migration from Old System

To migrate from the old upgrade system:

1. Ensure the database is at version 48 (latest)
2. Use `AlembicManager.transition_to_alembic()`
3. Future upgrades will use Alembic

## Future Work

- Implement proper downgrade operations for all migrations
- Add automatic migration generation from model changes
- Improve test coverage for complex migrations
- Add migration validation tools