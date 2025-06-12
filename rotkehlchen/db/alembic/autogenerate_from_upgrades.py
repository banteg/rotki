#!/usr/bin/env python3
"""
Script to generate Alembic migrations by running old upgrade scripts sequentially
and using Alembic's autogenerate feature to capture the schema changes.
"""

import importlib.util
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    HAS_SQLCIPHER = True
except ImportError:
    HAS_SQLCIPHER = False
    sqlcipher = None


class MockProgressHandler:
    """Mock progress handler for upgrades"""
    
    def __init__(self):
        self.current_round = 0
        self.rounds_total = 1
        
    def set_total_steps(self, steps: int) -> None:
        self.steps = steps
        
    def new_step(self, name: str) -> None:
        print(f"    Step: {name}")


class AlembicMigrationGenerator:
    """Generate Alembic migrations from old upgrade scripts"""
    
    def __init__(self):
        self.db_dir = Path(__file__).parent.parent
        self.upgrades_dir = self.db_dir / "upgrades"
        self.alembic_dir = self.db_dir / "alembic"
        self.versions_dir = self.alembic_dir / "versions"
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_data_dir = Path(__file__).parent.parent.parent.parent / "rotkehlchen" / "tests" / "data"
        self.password = "123"  # Standard test database password
        
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            
    def get_test_db_path(self, version: int) -> Optional[Path]:
        """Get the path to a test database for a specific version"""
        db_path = self.test_data_dir / f"v{version}_rotkehlchen.db"
        return db_path if db_path.exists() else None
        
    def decrypt_database(self, encrypted_db_path: Path, decrypted_db_path: Path) -> None:
        """Decrypt an encrypted database to a regular SQLite database"""
        if not HAS_SQLCIPHER:
            raise ImportError("pysqlcipher3 is required to decrypt test databases")
            
        print(f"  Decrypting {encrypted_db_path.name}...")
        
        # Open encrypted database
        encrypted_conn = sqlcipher.connect(str(encrypted_db_path))
        encrypted_conn.execute(f"PRAGMA key = '{self.password}'")
        
        # Export to regular SQLite database
        encrypted_conn.execute(f"ATTACH DATABASE '{decrypted_db_path}' AS plaintext KEY ''")
        encrypted_conn.execute("SELECT sqlcipher_export('plaintext')")
        encrypted_conn.execute("DETACH DATABASE plaintext")
        encrypted_conn.close()
        
    def create_database_at_version(self, version: int) -> Path:
        """Create a database at a specific version by applying upgrades sequentially"""
        db_path = self.temp_dir / f"v{version}_generated.db"
        
        # Try to find a test database close to our target version
        start_version = version
        source_db = None
        
        # Look for the closest available test database
        while start_version >= 26 and source_db is None:
            source_db = self.get_test_db_path(start_version)
            if not source_db:
                start_version -= 1
                
        if not source_db:
            raise FileNotFoundError("No suitable test database found")
            
        print(f"  Using v{start_version} as base database")
        
        # Decrypt the database if we have sqlcipher
        if HAS_SQLCIPHER:
            self.decrypt_database(source_db, db_path)
        else:
            # Try to copy anyway - might be unencrypted
            shutil.copy(source_db, db_path)
        
        # Apply upgrades to reach target version
        if start_version < version:
            self.apply_upgrades_to_version(db_path, start_version, version)
            
        return db_path
    
    def apply_upgrades_to_version(self, db_path: Path, from_version: int, to_version: int) -> None:
        """Apply upgrade scripts from one version to another"""
        print(f"  Applying upgrades from v{from_version} to v{to_version}...")
        
        # Create a connection
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        for version in range(from_version, to_version):
            upgrade_file = self.upgrades_dir / f"v{version}_v{version+1}.py"
            if not upgrade_file.exists():
                print(f"    Skipping v{version} -> v{version+1} (no upgrade file)")
                continue
                
            print(f"    Applying v{version} -> v{version+1}...")
            
            try:
                # Import the upgrade module
                spec = importlib.util.spec_from_file_location(f"v{version}_v{version+1}", upgrade_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Create mock progress handler
                progress_handler = MockProgressHandler()
                
                # Run the upgrade function
                if hasattr(module, '_do_upgrade'):
                    module._do_upgrade(cursor, progress_handler)
                elif hasattr(module, f'upgrade_v{version}_to_v{version+1}'):
                    upgrade_func = getattr(module, f'upgrade_v{version}_to_v{version+1}')
                    upgrade_func(cursor, progress_handler)
                else:
                    print(f"      Warning: No upgrade function found")
                    
                # Update version
                cursor.execute('PRAGMA user_version = ?', (version + 1,))
                conn.commit()
                
            except Exception as e:
                print(f"      Error: {e}")
                conn.rollback()
                raise
                
        conn.close()
        
    def get_schema_info(self, db_path: Path) -> Dict[str, any]:
        """Extract comprehensive schema information from a database"""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        schema = {
            'tables': {},
            'indexes': {},
            'triggers': {},
            'views': {}
        }
        
        # Get tables
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        for name, sql in cursor.fetchall():
            schema['tables'][name] = {
                'sql': sql,
                'columns': []
            }
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({name})")
            for col_info in cursor.fetchall():
                schema['tables'][name]['columns'].append({
                    'cid': col_info[0],
                    'name': col_info[1],
                    'type': col_info[2],
                    'notnull': col_info[3],
                    'default': col_info[4],
                    'pk': col_info[5]
                })
        
        # Get indexes
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='index' AND sql IS NOT NULL
            ORDER BY name
        """)
        for name, sql in cursor.fetchall():
            schema['indexes'][name] = sql
            
        # Get triggers
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='trigger'
            ORDER BY name
        """)
        for name, sql in cursor.fetchall():
            schema['triggers'][name] = sql
            
        # Get views
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='view'
            ORDER BY name
        """)
        for name, sql in cursor.fetchall():
            schema['views'][name] = sql
            
        conn.close()
        return schema
        
    def compare_schemas(self, old_schema: Dict, new_schema: Dict) -> List[str]:
        """Compare two schemas and generate Alembic operations"""
        operations = []
        
        # Compare tables
        old_tables = set(old_schema['tables'].keys())
        new_tables = set(new_schema['tables'].keys())
        
        # Dropped tables
        for table in old_tables - new_tables:
            operations.append(f"    op.drop_table('{table}')")
            
        # New tables
        for table in new_tables - old_tables:
            operations.append(f"    # Create table {table}")
            sql = new_schema['tables'][table]['sql']
            # Clean up SQL for Alembic
            sql = sql.replace('\n', '\n    ')
            operations.append(f"    op.execute('''\n    {sql}\n    ''')")
            
        # Modified tables
        for table in old_tables & new_tables:
            old_cols = {c['name']: c for c in old_schema['tables'][table]['columns']}
            new_cols = {c['name']: c for c in new_schema['tables'][table]['columns']}
            
            # Check for column changes
            old_col_names = set(old_cols.keys())
            new_col_names = set(new_cols.keys())
            
            # Dropped columns
            for col in old_col_names - new_col_names:
                operations.append(f"    op.drop_column('{table}', '{col}')")
                
            # New columns
            for col in new_col_names - old_col_names:
                col_info = new_cols[col]
                nullable = not col_info['notnull']
                default = col_info['default']
                
                col_def = f"sa.Column('{col}', sa.{col_info['type']}"
                if not nullable:
                    col_def += ", nullable=False"
                if default is not None:
                    col_def += f", server_default='{default}'"
                col_def += ")"
                
                operations.append(f"    op.add_column('{table}', {col_def})")
                
        # Compare indexes
        old_indexes = set(old_schema['indexes'].keys())
        new_indexes = set(new_schema['indexes'].keys())
        
        for idx in old_indexes - new_indexes:
            operations.append(f"    op.drop_index('{idx}')")
            
        for idx in new_indexes - old_indexes:
            sql = new_schema['indexes'][idx]
            operations.append(f"    op.execute('''{sql}''')")
            
        return operations
        
    def generate_migration_for_version(self, from_version: int, to_version: int) -> None:
        """Generate a migration for a specific version upgrade"""
        print(f"\nGenerating migration for v{from_version} -> v{to_version}...")
        
        try:
            # Create databases at both versions
            from_db = self.create_database_at_version(from_version)
            to_db = self.create_database_at_version(to_version)
            
            # Get schemas
            from_schema = self.get_schema_info(from_db)
            to_schema = self.get_schema_info(to_db)
            
            # Compare schemas
            operations = self.compare_schemas(from_schema, to_schema)
            
            # Create migration file
            revision_id = f"{from_version:03d}_v{from_version}_to_v{to_version}"
            prev_revision = f"{from_version-1:03d}_v{from_version-1}_to_v{from_version}" if from_version > 26 else "001_initial_v26"
            
            migration_content = f'''"""v{from_version} to v{to_version}

Revision ID: {revision_id}
Revises: {prev_revision}
Create Date: 2025-01-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = '{prev_revision}'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v{from_version} to v{to_version}"""
{chr(10).join(operations) if operations else "    pass"}


def downgrade() -> None:
    """Downgrade from v{to_version} to v{from_version}"""
    # Downgrade operations would need to be implemented
    raise NotImplementedError("Downgrade not implemented")
'''
            
            # Check if file already exists
            output_file = self.versions_dir / f"{revision_id}.py"
            if output_file.exists():
                # Create with _new suffix
                output_file = self.versions_dir / f"{revision_id}_new.py"
                
            output_file.write_text(migration_content)
            print(f"  Created: {output_file.name}")
            
        except Exception as e:
            print(f"  Error: {e}")
            raise
            
    def generate_all_migrations(self, start_version: int = 26, end_version: int = 48) -> None:
        """Generate all migrations"""
        successful = []
        failed = []
        
        for version in range(start_version, end_version):
            try:
                self.generate_migration_for_version(version, version + 1)
                successful.append(version)
            except Exception as e:
                print(f"  Failed to generate v{version} -> v{version+1}: {e}")
                failed.append(version)
                
        print(f"\nSummary:")
        print(f"  Successful: {len(successful)} migrations")
        print(f"  Failed: {len(failed)} migrations")
        
        if failed:
            print(f"  Failed versions: {failed}")
            

def main():
    """Main entry point"""
    if not HAS_SQLCIPHER:
        print("Warning: pysqlcipher3 not available. Will try to work with unencrypted databases.")
        
    generator = AlembicMigrationGenerator()
    
    try:
        # Check if all test databases exist
        print("Checking available test databases...")
        available_versions = []
        for v in range(26, 48):
            if generator.get_test_db_path(v):
                available_versions.append(v)
                
        print(f"Available test databases: {available_versions}")
        
        # Test with a single migration first
        print("\nTesting migration generation with v26 -> v27...")
        generator.generate_migration_for_version(26, 27)
        
        # Generate all migrations
        print("\nGenerating all migrations...")
        generator.generate_all_migrations()
            
    finally:
        generator.cleanup()
        
    print("\nDone! Review the generated migrations in:")
    print(f"  {generator.versions_dir}")
        

if __name__ == '__main__':
    main()