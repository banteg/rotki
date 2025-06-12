# Alembic Migrations for Rotkehlchen

This directory contains Alembic migration scripts for managing database schema changes in Rotkehlchen.

## Overview

Alembic is integrated to work alongside the existing manual upgrade system in `db/upgrades/`. 

### When to use Alembic vs Manual Upgrades

- **Use Alembic for**:
  - New schema changes after migrating to SQLModel
  - Schema changes that can be auto-generated from model changes
  - Development and testing of schema migrations
  
- **Continue using manual upgrades for**:
  - Complex data migrations
  - Backwards compatibility with older Rotkehlchen versions
  - Any changes that need to support users upgrading from pre-SQLModel versions

## Usage

### Generate a new migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to history_events"

# Create empty migration for manual changes
alembic revision -m "Complex data migration"
```

### Run migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision>

# Downgrade one revision
alembic downgrade -1
```

### Check current status

```bash
alembic current
alembic history
```

## Integration with Rotkehlchen

The Alembic migrations are designed to:

1. Use the same database connection as Rotkehlchen
2. Work with SQLite's limitations (using batch operations)
3. Coexist with the manual upgrade system
4. Support the existing version tracking in the `settings` table

## Best Practices

1. Always test migrations on a copy of the database first
2. Include both upgrade and downgrade operations when possible
3. Use descriptive messages for migrations
4. Keep migrations atomic and focused on a single change
5. Document any manual steps required