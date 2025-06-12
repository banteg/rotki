#!/usr/bin/env python3
"""Script to port existing upgrade scripts to Alembic migrations

This script converts the existing upgrade functions (v26-v48) into proper
Alembic migration files.
"""

import ast
import importlib
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class UpgradePorter:
    """Converts rotkehlchen upgrade scripts to Alembic migrations"""
    
    def __init__(self):
        self.upgrades_path = Path(__file__).parent.parent / "upgrades"
        self.versions_path = Path(__file__).parent / "versions"
        self.versions_path.mkdir(exist_ok=True)
        
    def get_upgrade_files(self) -> List[Path]:
        """Get all upgrade files in order"""
        files = []
        for version in range(26, 48):
            file = self.upgrades_path / f"v{version}_v{version+1}.py"
            if file.exists():
                files.append(file)
        return files
    
    def extract_sql_operations(self, upgrade_file: Path) -> List[Dict[str, Any]]:
        """Extract SQL operations from an upgrade file"""
        operations = []
        
        # Read the file content
        content = upgrade_file.read_text()
        
        # Parse the AST to find SQL operations
        tree = ast.parse(content)
        
        # Look for common patterns
        sql_patterns = [
            (r'cursor\.execute\((.*?)\)', 'execute'),
            (r'cursor\.executemany\((.*?)\)', 'executemany'),
            (r'CREATE TABLE.*?;', 'create_table'),
            (r'ALTER TABLE.*?;', 'alter_table'),
            (r'DROP TABLE.*?;', 'drop_table'),
            (r'INSERT INTO.*?;', 'insert'),
            (r'UPDATE.*?;', 'update'),
            (r'DELETE FROM.*?;', 'delete'),
        ]
        
        # Extract operations using regex
        for pattern, op_type in sql_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            for match in matches:
                operations.append({
                    'type': op_type,
                    'sql': match.strip(),
                    'file': upgrade_file.name
                })
        
        return operations
    
    def convert_to_alembic_operation(self, operation: Dict[str, Any]) -> str:
        """Convert a SQL operation to an Alembic operation"""
        sql = operation['sql']
        op_type = operation['type']
        
        # Handle CREATE TABLE
        if op_type == 'create_table' or 'CREATE TABLE' in sql:
            # Extract table name
            match = re.search(r'CREATE TABLE (?:IF NOT EXISTS )?(.*?)\s*\(', sql, re.IGNORECASE)
            if match:
                table_name = match.group(1).strip()
                # This is simplified - actual implementation would parse columns
                return f"op.create_table('{table_name}', ...)"
        
        # Handle ALTER TABLE
        elif op_type == 'alter_table' or 'ALTER TABLE' in sql:
            match = re.search(r'ALTER TABLE\s+(.*?)\s+(.*)', sql, re.IGNORECASE)
            if match:
                table_name = match.group(1).strip()
                alteration = match.group(2).strip()
                if 'ADD COLUMN' in alteration.upper():
                    return f"op.add_column('{table_name}', ...)"
                elif 'DROP COLUMN' in alteration.upper():
                    return f"op.drop_column('{table_name}', ...)"
        
        # Handle DROP TABLE
        elif op_type == 'drop_table' or 'DROP TABLE' in sql:
            match = re.search(r'DROP TABLE (?:IF EXISTS )?(.*?)(?:\s|;|$)', sql, re.IGNORECASE)
            if match:
                table_name = match.group(1).strip()
                return f"op.drop_table('{table_name}')"
        
        # Default: use execute for complex operations
        return f"op.execute({repr(sql)})"
    
    def create_migration_file(self, version_from: int, version_to: int, operations: List[str]) -> str:
        """Create an Alembic migration file content"""
        revision_id = f"{version_from:03d}_v{version_from}_to_v{version_to}"
        prev_revision = f"{version_from-1:03d}_v{version_from-1}_to_v{version_from}" if version_from > 26 else "001_initial_v48"
        
        template = f'''"""Upgrade from v{version_from} to v{version_to}

Revision ID: {revision_id}
Revises: {prev_revision}
Create Date: 2025-01-06

Original upgrade function from rotkehlchen v{version_from}_v{version_to}.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = '{prev_revision}'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade from v{version_from} to v{version_to}"""
    # Operations ported from the original upgrade script
    {"    ".join(operations)}


def downgrade() -> None:
    """Downgrade from v{version_to} to v{version_from}"""
    # Note: Downgrades were not supported in the original system
    # These would need to be implemented based on the upgrade operations
    raise NotImplementedError("Downgrade not implemented for this migration")
'''
        return template
    
    def port_all_upgrades(self):
        """Port all upgrade scripts to Alembic migrations"""
        upgrade_files = self.get_upgrade_files()
        
        for upgrade_file in upgrade_files:
            # Extract version numbers
            match = re.search(r'v(\d+)_v(\d+)\.py', upgrade_file.name)
            if not match:
                continue
                
            version_from = int(match.group(1))
            version_to = int(match.group(2))
            
            print(f"Porting {upgrade_file.name}...")
            
            # Extract operations
            operations = self.extract_sql_operations(upgrade_file)
            
            # Convert to Alembic operations
            alembic_ops = []
            for op in operations:
                alembic_op = self.convert_to_alembic_operation(op)
                if alembic_op:
                    alembic_ops.append(alembic_op + "\n")
            
            # Create migration file
            migration_content = self.create_migration_file(version_from, version_to, alembic_ops)
            
            # Write migration file
            migration_file = self.versions_path / f"{version_from:03d}_v{version_from}_to_v{version_to}.py"
            migration_file.write_text(migration_content)
            
            print(f"  Created {migration_file.name}")
        
        print("\nMigration porting complete!")
        print("\nNext steps:")
        print("1. Review each generated migration file")
        print("2. Complete the conversion of complex operations")
        print("3. Test the migrations on a copy of the database")
        print("4. Implement downgrade operations where possible")


if __name__ == '__main__':
    porter = UpgradePorter()
    porter.port_all_upgrades()