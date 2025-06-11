#!/usr/bin/env python3
"""Test to verify ORM models create identical schemas to the original SQL definitions"""

import sqlite3
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

# Import schema definitions
from rotkehlchen.db.schema import (
    DB_CREATE_LOCATION,
    DB_CREATE_BALANCE_CATEGORY,
    DB_CREATE_ASSETS,
    DB_CREATE_IGNORED_ACTIONS,
    DB_CREATE_TIMED_BALANCES,
    DB_CREATE_TIMED_LOCATION_DATA,
    DB_CREATE_TAG_MAPPINGS,
    DB_CREATE_TAGS_TABLE,
    DB_CREATE_MULTISETTINGS,
    DB_CREATE_SETTINGS,
    DB_CREATE_USER_CREDENTIALS,
    DB_CREATE_USER_CREDENTIALS_MAPPINGS,
    DB_CREATE_EXTERNAL_SERVICE_CREDENTIALS,
    DB_CREATE_BLOCKCHAIN_ACCOUNTS,
    DB_CREATE_MANUALLY_TRACKED_BALANCES,
)

from rotkehlchen.db.orm.base import UserDBBase
from rotkehlchen.db.orm import (
    Location, BalanceCategory, Asset, Tag, UserSettings, UserCredentials,
    UserCredentialMapping, BlockchainAccount, TimedBalance, TimedLocationData,
    ManuallyTrackedBalance, ExternalServiceCredentials, MultiSettings,
    IgnoredAction,
)


def get_table_info(conn):
    """Extract table information from a SQLite database"""
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row[0] for row in cursor.fetchall()}
    
    table_info = {}
    
    for table in tables:
        # Get column info
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns = {}
        for row in cursor.fetchall():
            columns[row[1]] = {
                'type': row[2],
                'notnull': bool(row[3]),
                'default': row[4],
                'pk': row[5]
            }
        
        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list('{table}')")
        foreign_keys = []
        for row in cursor.fetchall():
            foreign_keys.append({
                'column': row[3],
                'ref_table': row[2],
                'ref_column': row[4],
                'on_update': row[5],
                'on_delete': row[6]
            })
        
        table_info[table] = {
            'columns': columns,
            'foreign_keys': foreign_keys,
        }
    
    return table_info


def normalize_type(type_str):
    """Normalize SQL type strings for comparison"""
    type_str = type_str.upper()
    # Convert VARCHAR[n] to VARCHAR(n) for comparison
    if 'VARCHAR[' in type_str:
        type_str = type_str.replace('[', '(').replace(']', ')')
    return type_str


def compare_schemas(old_info, new_info):
    """Compare two schema definitions and report differences"""
    differences = []
    
    # Check for missing/extra tables
    old_tables = set(old_info.keys())
    new_tables = set(new_info.keys())
    
    missing_tables = old_tables - new_tables
    extra_tables = new_tables - old_tables
    
    if missing_tables:
        differences.append(f"Missing tables in ORM: {missing_tables}")
    if extra_tables:
        differences.append(f"Extra tables in ORM: {extra_tables}")
    
    # Compare common tables
    common_tables = old_tables & new_tables
    
    for table in sorted(common_tables):
        old_table = old_info[table]
        new_table = new_info[table]
        
        # Compare columns
        old_cols = set(old_table['columns'].keys())
        new_cols = set(new_table['columns'].keys())
        
        if old_cols != new_cols:
            missing_cols = old_cols - new_cols
            extra_cols = new_cols - old_cols
            if missing_cols:
                differences.append(f"{table}: Missing columns {missing_cols}")
            if extra_cols:
                differences.append(f"{table}: Extra columns {extra_cols}")
        
        # Compare column properties
        for col in old_cols & new_cols:
            old_col = old_table['columns'][col]
            new_col = new_table['columns'][col]
            
            # Compare types (normalize for comparison)
            old_type = normalize_type(old_col['type'])
            new_type = normalize_type(new_col['type'])
            
            if old_type != new_type:
                differences.append(f"{table}.{col}: Type mismatch - old: {old_type}, new: {new_type}")
            
            if old_col['notnull'] != new_col['notnull']:
                differences.append(f"{table}.{col}: NOT NULL mismatch - old: {old_col['notnull']}, new: {new_col['notnull']}")
        
        # Compare foreign keys
        old_fks = {(fk['column'], fk['ref_table'], fk['ref_column']) for fk in old_table['foreign_keys']}
        new_fks = {(fk['column'], fk['ref_table'], fk['ref_column']) for fk in new_table['foreign_keys']}
        
        if old_fks != new_fks:
            missing_fks = old_fks - new_fks
            extra_fks = new_fks - old_fks
            if missing_fks:
                differences.append(f"{table}: Missing foreign keys {missing_fks}")
            if extra_fks:
                differences.append(f"{table}: Extra foreign keys {extra_fks}")
    
    return differences


class TestSchemaCompatibility:
    """Test that ORM models generate identical schemas to SQL definitions"""
    
    def test_basic_tables(self, tmp_path):
        """Test basic table schemas match between SQL and ORM"""
        # Create old-style database
        old_db_path = tmp_path / "old_style.db"
        old_conn = sqlite3.connect(str(old_db_path))
        old_cursor = old_conn.cursor()
        
        # Execute CREATE TABLE statements
        schemas = [
            DB_CREATE_LOCATION,
            DB_CREATE_BALANCE_CATEGORY,
            DB_CREATE_ASSETS,
            DB_CREATE_TAGS_TABLE,
            DB_CREATE_TAG_MAPPINGS,
            DB_CREATE_SETTINGS,
            DB_CREATE_MULTISETTINGS,
            DB_CREATE_USER_CREDENTIALS,
            DB_CREATE_USER_CREDENTIALS_MAPPINGS,
            DB_CREATE_EXTERNAL_SERVICE_CREDENTIALS,
            DB_CREATE_BLOCKCHAIN_ACCOUNTS,
            DB_CREATE_TIMED_BALANCES,
            DB_CREATE_TIMED_LOCATION_DATA,
            DB_CREATE_MANUALLY_TRACKED_BALANCES,
            DB_CREATE_IGNORED_ACTIONS,
        ]
        
        for schema in schemas:
            old_cursor.executescript(schema)
        
        old_conn.commit()
        
        # Create ORM-based database
        orm_db_path = tmp_path / "orm_style.db"
        engine = create_engine(f"sqlite:///{orm_db_path}")
        UserDBBase.metadata.create_all(engine)
        
        # Get schema info
        old_info = get_table_info(old_conn)
        
        orm_conn = sqlite3.connect(str(orm_db_path))
        new_info = get_table_info(orm_conn)
        
        # Compare schemas
        differences = compare_schemas(old_info, new_info)
        
        # Close connections
        old_conn.close()
        orm_conn.close()
        
        # Report differences
        if differences:
            print("\n❌ Schema differences found:")
            for diff in differences:
                print(f"  - {diff}")
            pytest.fail(f"Found {len(differences)} schema differences")
        else:
            print("\n✅ Schemas are identical!")
    
    def test_assets_table_specifically(self, tmp_path):
        """Test assets table schema specifically"""
        # Create old-style database
        old_db_path = tmp_path / "old_assets.db"
        old_conn = sqlite3.connect(str(old_db_path))
        old_cursor = old_conn.cursor()
        
        # Create only assets table
        old_cursor.executescript(DB_CREATE_ASSETS)
        old_conn.commit()
        
        # Create ORM database with only Asset model
        orm_db_path = tmp_path / "orm_assets.db"
        engine = create_engine(f"sqlite:///{orm_db_path}")
        Asset.__table__.create(engine)
        
        # Get column info
        old_cursor.execute("PRAGMA table_info('assets')")
        old_columns = {row[1]: row[2] for row in old_cursor.fetchall()}
        
        orm_conn = sqlite3.connect(str(orm_db_path))
        orm_cursor = orm_conn.cursor()
        orm_cursor.execute("PRAGMA table_info('assets')")
        orm_columns = {row[1]: row[2] for row in orm_cursor.fetchall()}
        
        print(f"\nOld assets columns: {old_columns}")
        print(f"ORM assets columns: {orm_columns}")
        
        old_conn.close()
        orm_conn.close()
        
        assert old_columns == orm_columns, f"Assets table columns mismatch: SQL={old_columns}, ORM={orm_columns}"