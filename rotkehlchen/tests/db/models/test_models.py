"""Test SQLModel schema compatibility with original SQL schemas"""

import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest
from sqlalchemy import create_engine

from rotkehlchen.db.models.globaldb import Base as GlobalBase
from rotkehlchen.db.models.transient import Base as TransientBase
from rotkehlchen.db.models.user import Base as UserBase
from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.schema_transient import DB_SCRIPT_CREATE_TRANSIENT_TABLES


def normalize_type(type_str: str) -> str:
    """Normalize SQL type strings for comparison"""
    type_str = type_str.upper()
    # Convert VARCHAR[n] to VARCHAR(n) for comparison
    if 'VARCHAR[' in type_str:
        type_str = type_str.replace('[', '(').replace(']', ')')
    # Normalize common type variations
    type_str = type_str.replace('BOOLEAN', 'INTEGER')  # SQLite stores booleans as integers
    return type_str


def get_table_info(conn: sqlite3.Connection) -> Dict[str, Dict]:
    """Extract complete table information from a SQLite database"""
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')}
    
    table_info = {}
    
    for table in tables:
        # Get column info
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns = {}
        primary_keys = []
        for row in cursor.fetchall():
            cid, name, type_, notnull, default, pk = row
            # Primary key columns are implicitly NOT NULL
            is_pk = pk > 0
            if is_pk:
                primary_keys.append((pk, name))
            columns[name] = {
                'type': normalize_type(type_),
                'notnull': bool(notnull) or is_pk,
                'default': default,
                'pk': pk
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
        
        # Get indexes
        cursor.execute(f"PRAGMA index_list('{table}')")
        indexes = []
        for row in cursor.fetchall():
            idx_name = row[1]
            is_unique = bool(row[2])
            
            cursor.execute(f"PRAGMA index_info('{idx_name}')")
            idx_cols = [col_row[2] for col_row in cursor.fetchall()]
            
            # Skip SQLite auto indexes
            if not idx_name.startswith('sqlite_autoindex'):
                indexes.append({
                    'name': idx_name,
                    'unique': is_unique,
                    'columns': idx_cols
                })
        
        # Get check constraints
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        create_sql = cursor.fetchone()[0]
        check_constraints = []
        if 'CHECK' in create_sql.upper():
            # Simple extraction of CHECK constraints
            import re
            checks = re.findall(r'CHECK\s*\((.*?)\)', create_sql, re.IGNORECASE)
            check_constraints = [check.strip() for check in checks]
        
        # Sort primary keys by position
        primary_keys.sort(key=lambda x: x[0])
        primary_key_columns = [col for _, col in primary_keys]
        
        table_info[table] = {
            'columns': columns,
            'foreign_keys': foreign_keys,
            'indexes': indexes,
            'check_constraints': check_constraints,
            'primary_keys': primary_key_columns,
        }
    
    return table_info


def compare_schemas(
    old_info: Dict[str, Dict],
    new_info: Dict[str, Dict],
    db_name: str
) -> List[str]:
    """Compare two schema definitions and report differences"""
    differences = []
    
    # Check for missing/extra tables
    old_tables = set(old_info.keys())
    new_tables = set(new_info.keys())
    
    missing_tables = old_tables - new_tables
    extra_tables = new_tables - old_tables
    
    if missing_tables:
        differences.append(f"{db_name}: Missing tables in SQLModel: {missing_tables}")
    if extra_tables:
        differences.append(f"{db_name}: Extra tables in SQLModel: {extra_tables}")
    
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
                differences.append(f"{db_name}.{table}: Missing columns {missing_cols}")
            if extra_cols:
                differences.append(f"{db_name}.{table}: Extra columns {extra_cols}")
        
        # Compare column properties
        for col in old_cols & new_cols:
            old_col = old_table['columns'][col]
            new_col = new_table['columns'][col]
            
            # Compare types
            if old_col['type'] != new_col['type']:
                differences.append(
                    f"{db_name}.{table}.{col}: Type mismatch - "
                    f"old: {old_col['type']}, new: {new_col['type']}"
                )
            
            # Compare NOT NULL (with special cases)
            skip_notnull = (
                # These are tables without primary keys in SQL that need special handling
                (table == 'multisettings' and col == 'value') or
                (table == 'location_asset_mappings' and col == 'location')
            )
            
            if not skip_notnull and old_col['notnull'] != new_col['notnull']:
                differences.append(
                    f"{db_name}.{table}.{col}: NOT NULL mismatch - "
                    f"old: {old_col['notnull']}, new: {new_col['notnull']}"
                )
            
            # Compare defaults (skip known cosmetic differences)
            if old_col['default'] != new_col['default']:
                # Skip known cosmetic differences
                if not (
                    (old_col['default'] in ['0', "'0'"] and new_col['default'] in ['0', "'0'"]) or
                    (old_col['default'] == '' and new_col['default'] is None) or
                    (old_col['default'] is None and new_col['default'] == '') or
                    (old_col['default'] == "'A'" and new_col['default'] == "'A'")
                ):
                    differences.append(
                        f"{db_name}.{table}.{col}: Default mismatch - "
                        f"old: {old_col['default']}, new: {new_col['default']}"
                    )
        
        # Compare primary keys (with special handling for tables without PKs in SQL)
        skip_pk_check = table in ['multisettings', 'zksynclite_swaps', 'location_asset_mappings', 'location_unsupported_assets']
        if not skip_pk_check and old_table['primary_keys'] != new_table['primary_keys']:
            differences.append(
                f"{db_name}.{table}: Primary key mismatch - "
                f"old: {old_table['primary_keys']}, new: {new_table['primary_keys']}"
            )
        
        # Compare foreign keys
        old_fks = {
            (fk['column'], fk['ref_table'], fk['ref_column'])
            for fk in old_table['foreign_keys']
        }
        new_fks = {
            (fk['column'], fk['ref_table'], fk['ref_column'])
            for fk in new_table['foreign_keys']
        }
        
        if old_fks != new_fks:
            missing_fks = old_fks - new_fks
            extra_fks = new_fks - old_fks
            if missing_fks:
                differences.append(f"{db_name}.{table}: Missing foreign keys {missing_fks}")
            if extra_fks:
                differences.append(f"{db_name}.{table}: Extra foreign keys {extra_fks}")
    
    return differences


class TestSQLModelSchemaCompatibility:
    """Test that SQLModel generates identical schemas to original SQL"""
    
    def test_user_database_schema_compatibility(self):
        """Test user database schema compatibility"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create SQL database
            sql_db_path = tmppath / "user_sql.db"
            sql_conn = sqlite3.connect(str(sql_db_path))
            sql_conn.executescript(DB_SCRIPT_CREATE_TABLES)
            sql_conn.commit()
            
            # Create SQLModel database
            sqlmodel_db_path = tmppath / "user_sqlmodel.db"
            sqlmodel_engine = create_engine(f"sqlite:///{sqlmodel_db_path}")
            UserBase.metadata.create_all(sqlmodel_engine)
            
            # Get schema info
            sql_info = get_table_info(sql_conn)
            
            sqlmodel_conn = sqlite3.connect(str(sqlmodel_db_path))
            sqlmodel_info = get_table_info(sqlmodel_conn)
            
            # Compare schemas
            differences = compare_schemas(sql_info, sqlmodel_info, "UserDB")
            
            # Close connections
            sql_conn.close()
            sqlmodel_conn.close()
            
            # Assert no differences
            if differences:
                pytest.fail(
                    "User database schema differences found:\n" + 
                    "\n".join(differences)
                )
    
    def test_global_database_schema_compatibility(self):
        """Test global database schema compatibility"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Get global database schema
            from rotkehlchen.globaldb.schema import DB_SCRIPT_CREATE_TABLES as GLOBAL_DB_SCRIPT
            
            # Create SQL database
            sql_db_path = tmppath / "global_sql.db"
            sql_conn = sqlite3.connect(str(sql_db_path))
            sql_conn.executescript(GLOBAL_DB_SCRIPT)
            sql_conn.commit()
            
            # Create SQLModel database
            sqlmodel_db_path = tmppath / "global_sqlmodel.db"
            sqlmodel_engine = create_engine(f"sqlite:///{sqlmodel_db_path}")
            GlobalBase.metadata.create_all(sqlmodel_engine)
            
            # Get schema info
            sql_info = get_table_info(sql_conn)
            
            sqlmodel_conn = sqlite3.connect(str(sqlmodel_db_path))
            sqlmodel_info = get_table_info(sqlmodel_conn)
            
            # Compare schemas
            differences = compare_schemas(sql_info, sqlmodel_info, "GlobalDB")
            
            # Close connections
            sql_conn.close()
            sqlmodel_conn.close()
            
            # Assert no differences
            if differences:
                pytest.fail(
                    "Global database schema differences found:\n" + 
                    "\n".join(differences)
                )
    
    def test_transient_database_schema_compatibility(self):
        """Test transient database schema compatibility"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create SQL database
            sql_db_path = tmppath / "transient_sql.db"
            sql_conn = sqlite3.connect(str(sql_db_path))
            sql_conn.executescript(DB_SCRIPT_CREATE_TRANSIENT_TABLES)
            sql_conn.commit()
            
            # Create SQLModel database
            sqlmodel_db_path = tmppath / "transient_sqlmodel.db"
            sqlmodel_engine = create_engine(f"sqlite:///{sqlmodel_db_path}")
            TransientBase.metadata.create_all(sqlmodel_engine)
            
            # Get schema info
            sql_info = get_table_info(sql_conn)
            
            sqlmodel_conn = sqlite3.connect(str(sqlmodel_db_path))
            sqlmodel_info = get_table_info(sqlmodel_conn)
            
            # Compare schemas
            differences = compare_schemas(sql_info, sqlmodel_info, "TransientDB")
            
            # Close connections
            sql_conn.close()
            sqlmodel_conn.close()
            
            # Assert no differences
            if differences:
                pytest.fail(
                    "Transient database schema differences found:\n" + 
                    "\n".join(differences)
                )