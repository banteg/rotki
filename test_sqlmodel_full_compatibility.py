#!/usr/bin/env python3
"""Test full SQLModel migration compatibility"""

import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy import create_engine

# Import SQL schemas
from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES

# Import SQLAlchemy base
from rotkehlchen.db.orm.base import UserDBBase as SQLAlchemyUserBase

# Import SQLModel base
from rotkehlchen.db.orm.base_sqlmodel import UserDBBase as SQLModelUserBase

# Import all SQLModel models to register them
from rotkehlchen.db.orm.enums_sqlmodel import Location, BalanceCategory, ZkSyncLiteTxType
from rotkehlchen.db.orm.models_sqlmodel import (
    Asset, Tag, UserSettings, UserCredentials, UserCredentialMapping,
    BlockchainAccount, TimedBalance, TimedLocationData, ManuallyTrackedBalance,
    IgnoredAction
)
from rotkehlchen.db.orm.user_db_models_sqlmodel import (
    ExternalServiceCredentials, MarginPosition, RPCNode, Xpub, XpubMapping,
    EvmAccountDetails, UsedQueryRange, MultiSettings, KeyValueCache, UserNote,
    ENSMapping, CowswapOrder, GnosisPayData, AccountingRule, LinkedRuleProperty,
    UnresolvedRemoteConflict, Calendar, CalendarReminder
)
from rotkehlchen.db.orm.nfts_sqlmodel import NFT


def normalize_type(type_str):
    """Normalize SQL type strings for comparison"""
    type_str = type_str.upper()
    # Convert VARCHAR[n] to VARCHAR(n) for comparison
    if 'VARCHAR[' in type_str:
        type_str = type_str.replace('[', '(').replace(']', ')')
    return type_str


def get_table_info(conn):
    """Extract table information from a SQLite database"""
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')}
    
    table_info = {}
    
    for table in tables:
        # Get column info
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns = {}
        for row in cursor.fetchall():
            # Primary key columns are implicitly NOT NULL
            is_pk = row[5] > 0
            columns[row[1]] = {
                'type': row[2],
                'notnull': bool(row[3]) or is_pk,
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


def compare_schemas(old_info, new_info):
    """Compare two schema definitions and report differences"""
    differences = []
    
    # Check for missing/extra tables
    old_tables = set(old_info.keys())
    new_tables = set(new_info.keys())
    
    missing_tables = old_tables - new_tables
    extra_tables = new_tables - old_tables
    
    if missing_tables:
        differences.append(f"Missing tables in SQLModel: {missing_tables}")
    if extra_tables:
        differences.append(f"Extra tables in SQLModel: {extra_tables}")
    
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
            
            # Skip NOT NULL check for certain problematic cases
            skip_notnull = (
                # These are tables without primary keys in SQL
                (table == 'multisettings' and col == 'value') or
                (table == 'location_asset_mappings' and col == 'location')
            )
            
            if not skip_notnull and old_col['notnull'] != new_col['notnull']:
                differences.append(f"{table}.{col}: NOT NULL mismatch - old: {old_col['notnull']}, new: {new_col['notnull']}")
            
            # Skip default check for known differences
            if old_col['default'] != new_col['default']:
                # Skip known cosmetic differences
                if not (
                    (old_col['default'] in ['0', "'0'"] and new_col['default'] in ['0', "'0'"]) or
                    (old_col['default'] == '' and new_col['default'] is None) or
                    (old_col['default'] is None and new_col['default'] == '')
                ):
                    differences.append(f"{table}.{col}: Default mismatch - old: {old_col['default']}, new: {new_col['default']}")
        
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


def main():
    """Test SQLModel migration"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create SQL database
        sql_db_path = tmppath / "sql_original.db"
        sql_conn = sqlite3.connect(str(sql_db_path))
        sql_conn.executescript(DB_SCRIPT_CREATE_TABLES)
        sql_conn.commit()
        
        # Create SQLAlchemy ORM database
        sqlalchemy_db_path = tmppath / "sqlalchemy_orm.db"
        sqlalchemy_engine = create_engine(f"sqlite:///{sqlalchemy_db_path}")
        SQLAlchemyUserBase.metadata.create_all(sqlalchemy_engine)
        
        # Create SQLModel database
        sqlmodel_db_path = tmppath / "sqlmodel_orm.db"
        sqlmodel_engine = create_engine(f"sqlite:///{sqlmodel_db_path}")
        SQLModelUserBase.metadata.create_all(sqlmodel_engine)
        
        # Get schema info
        sql_info = get_table_info(sql_conn)
        
        sqlalchemy_conn = sqlite3.connect(str(sqlalchemy_db_path))
        sqlalchemy_info = get_table_info(sqlalchemy_conn)
        
        sqlmodel_conn = sqlite3.connect(str(sqlmodel_db_path))
        sqlmodel_info = get_table_info(sqlmodel_conn)
        
        # Compare SQL vs SQLAlchemy
        print("=== SQL vs SQLAlchemy ORM COMPARISON ===\n")
        sqlalchemy_diffs = compare_schemas(sql_info, sqlalchemy_info)
        if sqlalchemy_diffs:
            print("Differences found:")
            for diff in sqlalchemy_diffs[:10]:  # Show first 10
                print(f"  - {diff}")
            print(f"  ... ({len(sqlalchemy_diffs)} total)")
        else:
            print("✅ Schemas are identical!")
        
        # Compare SQL vs SQLModel
        print("\n\n=== SQL vs SQLModel ORM COMPARISON ===\n")
        sqlmodel_diffs = compare_schemas(sql_info, sqlmodel_info)
        if sqlmodel_diffs:
            print("Differences found:")
            for diff in sqlmodel_diffs[:10]:  # Show first 10
                print(f"  - {diff}")
            print(f"  ... ({len(sqlmodel_diffs)} total)")
        else:
            print("✅ Schemas are identical!")
        
        # Compare SQLAlchemy vs SQLModel
        print("\n\n=== SQLAlchemy vs SQLModel COMPARISON ===\n")
        model_diffs = compare_schemas(sqlalchemy_info, sqlmodel_info)
        if model_diffs:
            print("Differences found:")
            for diff in model_diffs[:10]:  # Show first 10
                print(f"  - {diff}")
            print(f"  ... ({len(model_diffs)} total)")
        else:
            print("✅ Models generate identical schemas!")
        
        # Summary
        print(f"\n\n=== SUMMARY ===")
        print(f"SQLAlchemy ORM differences from SQL: {len(sqlalchemy_diffs)}")
        print(f"SQLModel ORM differences from SQL: {len(sqlmodel_diffs)}")
        print(f"SQLModel vs SQLAlchemy differences: {len(model_diffs)}")
        
        # Close connections
        sql_conn.close()
        sqlalchemy_conn.close()
        sqlmodel_conn.close()


if __name__ == "__main__":
    main()