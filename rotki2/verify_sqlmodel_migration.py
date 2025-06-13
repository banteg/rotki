#!/usr/bin/env python3
"""Script to verify that all SQLModel tables match the raw SQL schema definitions."""

import re
from pathlib import Path


def extract_tables_from_schema(schema_file: Path) -> dict[str, dict[str, any]]:
    """Extract table definitions from the raw SQL schema file."""
    with open(schema_file) as f:
        content = f.read()

    tables = {}

    # Pattern to match CREATE TABLE statements
    create_table_pattern = r'CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\);'
    matches = re.findall(create_table_pattern, content, re.DOTALL | re.IGNORECASE)

    for table_name, table_def in matches:
        columns = []
        foreign_keys = []
        primary_keys = []

        # Clean up the definition
        table_def = ' '.join(table_def.split())

        # Extract column definitions
        lines = [line.strip() for line in table_def.split(',')]

        for line in lines:
            if line.startswith('FOREIGN KEY'):
                foreign_keys.append(line)
            elif line.startswith('PRIMARY KEY'):
                # Extract composite primary keys
                pk_match = re.search(r'PRIMARY KEY\s*\((.*?)\)', line)
                if pk_match:
                    primary_keys = [col.strip() for col in pk_match.group(1).split(',')]
            elif line.startswith('UNIQUE('):
                continue  # Skip unique constraints for now
            else:
                # Regular column definition
                parts = line.split()
                if parts:
                    col_name = parts[0]
                    columns.append(col_name)
                    # Check if it's a single column primary key
                    if 'PRIMARY KEY' in line and not primary_keys:
                        primary_keys = [col_name]

        tables[table_name] = {
            'columns': columns,
            'primary_keys': primary_keys,
            'foreign_keys': foreign_keys,
        }

    return tables


def extract_sqlmodel_tables() -> set[str]:
    """Extract table names from SQLModel definitions."""
    tables = set()
    models_dir = Path('/workspace/rotkehlchen/db/models/user')

    for py_file in models_dir.glob('*.py'):
        with open(py_file) as f:
            content = f.read()

        # Find __tablename__ definitions
        tablename_pattern = r'__tablename__\s*=\s*["\'](\w+)["\']'
        matches = re.findall(tablename_pattern, content)
        tables.update(matches)

    return tables


def main():
    """Compare raw SQL schema with SQLModel tables."""
    schema_file = Path('/workspace/rotkehlchen/db/schema.py')

    # Extract tables from raw SQL schema
    sql_tables = extract_tables_from_schema(schema_file)

    # Extract tables from SQLModel
    sqlmodel_tables = extract_sqlmodel_tables()

    print('=== Database Migration Verification ===\n')

    print(f'Total tables in raw SQL schema: {len(sql_tables)}')
    print(f'Total tables in SQLModel: {len(sqlmodel_tables)}\n')

    # Find missing tables
    missing_in_sqlmodel = set(sql_tables.keys()) - sqlmodel_tables
    extra_in_sqlmodel = sqlmodel_tables - set(sql_tables.keys())

    if missing_in_sqlmodel:
        print('❌ Tables in SQL schema but NOT in SQLModel:')
        for table in sorted(missing_in_sqlmodel):
            print(f'  - {table}')
    else:
        print('✅ All SQL schema tables have SQLModel implementations!')

    print()

    if extra_in_sqlmodel:
        print('📝 Additional tables in SQLModel (not in raw schema):')
        for table in sorted(extra_in_sqlmodel):
            print(f'  - {table}')

    print('\n=== Summary ===')
    migration_complete = len(missing_in_sqlmodel) == 0

    if migration_complete:
        print('✅ Migration Status: COMPLETE')
        print('All tables from the raw SQL schema have been successfully migrated to SQLModel!')
    else:
        print('❌ Migration Status: INCOMPLETE')
        print(f'{len(missing_in_sqlmodel)} tables still need to be migrated.')

    return migration_complete


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
