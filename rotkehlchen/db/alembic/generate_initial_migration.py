#!/usr/bin/env python3
"""Generate the initial Alembic migration from current v48 schema

This script analyzes the current schema.py and generates a complete
Alembic migration file representing the v48 database state.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rotkehlchen.db import schema


class MigrationGenerator:
    """Generates Alembic migration from schema.py"""
    
    def __init__(self):
        self.tables_order = []
        self.table_definitions = {}
        self.enum_tables = ['location', 'balance_category', 'zksynclite_tx_type']
        self.indexes = []
        
    def extract_table_info(self, sql: str) -> Tuple[str, List[str]]:
        """Extract table name and column definitions from CREATE TABLE statement"""
        # Extract table name
        table_match = re.search(r'CREATE TABLE (?:IF NOT EXISTS )?(\w+)\s*\(', sql, re.IGNORECASE)
        if not table_match:
            return None, []
        
        table_name = table_match.group(1).strip()
        
        # Extract the content between CREATE TABLE and the final );
        # First, find the CREATE TABLE statement
        create_start = sql.find('CREATE TABLE')
        if create_start == -1:
            return table_name, []
        
        # Find the opening parenthesis
        paren_start = sql.find('(', create_start)
        if paren_start == -1:
            return table_name, []
        
        # Find the matching closing parenthesis
        paren_count = 1
        pos = paren_start + 1
        while paren_count > 0 and pos < len(sql):
            if sql[pos] == '(':
                paren_count += 1
            elif sql[pos] == ')':
                paren_count -= 1
            pos += 1
        
        if paren_count != 0:
            return table_name, []
        
        # Extract content between parentheses
        content = sql[paren_start + 1:pos - 1].strip()
        
        # Split by comma, but be careful with nested parentheses
        columns = []
        current_col = ''
        paren_depth = 0
        
        for char in content:
            if char == '(' :
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                col = current_col.strip()
                if col and not col.startswith('/*') and not col.startswith('INSERT'):
                    columns.append(col)
                current_col = ''
                continue
            current_col += char
        
        # Don't forget the last column
        if current_col.strip() and not current_col.strip().startswith('/*') and not current_col.strip().startswith('INSERT'):
            columns.append(current_col.strip())
        
        return table_name, columns
    
    def convert_column_definition(self, col_def: str) -> Dict[str, any]:
        """Convert SQL column definition to SQLAlchemy column args"""
        # Skip constraint definitions
        if col_def.strip().startswith(('FOREIGN KEY', 'PRIMARY KEY', 'UNIQUE(', 'CHECK(')):
            return None
            
        # Remove trailing comma if present
        col_def = col_def.rstrip(',')
        
        # Parse column name and type
        parts = col_def.split()
        if not parts:
            return None
            
        col_name = parts[0]
        col_info = {
            'name': col_name,
            'type': 'String',  # default
            'nullable': True,
            'primary_key': False,
            'foreign_keys': [],
            'unique': False,
            'server_default': None,
        }
        
        # Determine type
        if len(parts) > 1:
            sql_type = parts[1].upper()
            if sql_type in ['TEXT', 'VARCHAR', 'CHAR']:
                col_info['type'] = 'String'
                # Handle VARCHAR[n] or CHAR(n)
                if '[' in parts[1] or '(' in parts[1]:
                    size_match = re.search(r'[\[\(](\d+)[\]\)]', parts[1])
                    if size_match:
                        col_info['length'] = int(size_match.group(1))
            elif sql_type == 'INTEGER':
                col_info['type'] = 'Integer'
            elif sql_type == 'BLOB':
                col_info['type'] = 'LargeBinary'
            elif sql_type == 'REAL':
                col_info['type'] = 'Float'
        
        # Parse constraints
        col_def_upper = col_def.upper()
        if 'NOT NULL' in col_def_upper:
            col_info['nullable'] = False
        if 'PRIMARY KEY' in col_def_upper:
            col_info['primary_key'] = True
        if 'UNIQUE' in col_def_upper:
            col_info['unique'] = True
        if 'DEFAULT' in col_def_upper:
            default_match = re.search(r"DEFAULT\s*\(?'?([^)']+)'?\)?", col_def, re.IGNORECASE)
            if default_match:
                col_info['server_default'] = default_match.group(1)
        
        # Parse foreign keys
        fk_match = re.search(r'REFERENCES\s+(\w+)\s*\((\w+)\)', col_def, re.IGNORECASE)
        if fk_match:
            col_info['foreign_keys'].append({
                'table': fk_match.group(1),
                'column': fk_match.group(2)
            })
        
        return col_info
    
    def generate_column_code(self, col_info: Dict) -> str:
        """Generate SQLAlchemy column definition code"""
        if not col_info:
            return None
            
        parts = [f"sa.Column('{col_info['name']}'"]
        
        # Add type
        if col_info['type'] == 'String' and 'length' in col_info:
            if col_info['length'] == 1:
                parts.append("sa.CHAR(1)")
            else:
                parts.append(f"sa.VARCHAR({col_info['length']})")
        else:
            type_map = {
                'String': 'sa.TEXT',
                'Integer': 'sa.INTEGER',
                'LargeBinary': 'sa.BLOB',
                'Float': 'sa.REAL'
            }
            parts.append(type_map.get(col_info['type'], 'sa.TEXT'))
        
        # Add constraints
        if col_info['primary_key']:
            parts.append("primary_key=True")
        if not col_info['nullable']:
            parts.append("nullable=False")
        if col_info['unique'] and not col_info['primary_key']:
            parts.append("unique=True")
        if col_info['server_default']:
            parts.append(f"server_default='{col_info['server_default']}'")
        
        return ', '.join(parts) + ')'
    
    def generate_migration_content(self) -> str:
        """Generate the complete migration file content"""
        
        # Parse all table definitions
        for attr_name in dir(schema):
            if attr_name.startswith('DB_CREATE_'):
                sql = getattr(schema, attr_name)
                table_name, columns = self.extract_table_info(sql)
                if table_name:
                    self.table_definitions[table_name] = {
                        'sql': sql,
                        'columns': columns,
                        'attr_name': attr_name
                    }
        
        # Get table creation order from DB_SCRIPT_CREATE_TABLES
        script_lines = schema.DB_SCRIPT_CREATE_TABLES.split('\n')
        for line in script_lines:
            if line.strip().startswith('{DB_CREATE_'):
                attr_name = line.strip()[1:-1]  # Remove { and }
                for table_name, info in self.table_definitions.items():
                    if info['attr_name'] == attr_name:
                        self.tables_order.append(table_name)
                        break
        
        # Collect indexes
        for attr_name in dir(schema):
            if attr_name.startswith('DB_CREATE_') and 'INDEX' in attr_name:
                self.indexes.append(getattr(schema, attr_name))
        
        # Generate migration file
        migration = f'''"""Initial Alembic migration representing v48 schema

Revision ID: 001_initial_v48
Revises: 
Create Date: 2025-01-06

This migration creates the complete database schema as of v48.
It serves as the base for transitioning from the old upgrade system to Alembic.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_v48'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables for v48 schema"""
    
    # Create enum tables first
'''
        
        # Add enum tables
        for table in self.enum_tables:
            if table in self.table_definitions:
                migration += f"\n    # Create {table} enum table\n"
                migration += f"    op.create_table('{table}',\n"
                
                info = self.table_definitions[table]
                for col_line in info['columns']:
                    if col_line.strip() and not col_line.startswith('FOREIGN KEY') and not col_line.startswith('PRIMARY KEY'):
                        col_info = self.convert_column_definition(col_line)
                        if col_info:
                            col_code = self.generate_column_code(col_info)
                            if col_code:
                                migration += f"        {col_code},\n"
                
                # Add constraints
                if 'PRIMARY KEY' in info['sql']:
                    # Extract composite primary keys
                    pk_match = re.search(r'PRIMARY KEY\s*\(([^)]+)\)', info['sql'])
                    if pk_match:
                        pk_cols = [col.strip() for col in pk_match.group(1).split(',')]
                        migration += f"        sa.PrimaryKeyConstraint({', '.join(repr(col) for col in pk_cols)}),\n"
                
                migration += "    )\n"
                
                # Add enum values
                if table == 'location':
                    migration += self._generate_location_inserts()
                elif table == 'balance_category':
                    migration += self._generate_balance_category_inserts()
                elif table == 'zksynclite_tx_type':
                    migration += self._generate_zksynclite_type_inserts()
        
        # Add remaining tables
        migration += "\n    # Create main tables\n"
        for table in self.tables_order:
            if table not in self.enum_tables and table in self.table_definitions:
                migration += f"\n    op.create_table('{table}',\n"
                
                info = self.table_definitions[table]
                for col_line in info['columns']:
                    if col_line.strip() and not col_line.startswith('FOREIGN KEY') and not col_line.startswith('PRIMARY KEY') and not col_line.startswith('UNIQUE('):
                        col_info = self.convert_column_definition(col_line)
                        if col_info:
                            col_code = self.generate_column_code(col_info)
                            if col_code:
                                migration += f"        {col_code},\n"
                
                migration += "    )\n"
        
        # Add indexes
        migration += "\n    # Create indexes\n"
        for index_sql in self.indexes:
            if index_sql:
                # Extract index info
                match = re.search(r'CREATE INDEX (?:IF NOT EXISTS )?(\w+) ON (\w+)\((\w+)\)', index_sql)
                if match:
                    idx_name = match.group(1)
                    table_name = match.group(2)
                    column = match.group(3)
                    migration += f"    op.create_index('{idx_name}', '{table_name}', ['{column}'])\n"
        
        migration += '''

def downgrade() -> None:
    """Drop all tables"""
    # Drop indexes first
'''
        
        # Add index drops
        for index_sql in self.indexes:
            if index_sql:
                match = re.search(r'CREATE INDEX (?:IF NOT EXISTS )?(\w+) ON (\w+)', index_sql)
                if match:
                    idx_name = match.group(1)
                    table_name = match.group(2)
                    migration += f"    op.drop_index('{idx_name}', '{table_name}')\n"
        
        migration += "\n    # Drop tables in reverse order\n"
        
        # Drop tables in reverse order
        for table in reversed(self.tables_order):
            migration += f"    op.drop_table('{table}')\n"
        
        # Drop enum tables last
        for table in reversed(self.enum_tables):
            migration += f"    op.drop_table('{table}')\n"
        
        return migration
    
    def _generate_location_inserts(self) -> str:
        """Generate INSERT statements for location enum values"""
        inserts = "\n    # Insert location enum values\n"
        
        # Extract from schema.py
        location_sql = schema.DB_CREATE_LOCATION
        insert_matches = re.findall(r"INSERT OR IGNORE INTO location\(location, seq\) VALUES \('(.)', (\d+)\);", location_sql)
        
        for loc, seq in insert_matches:
            inserts += f"    op.execute(\"INSERT INTO location(location, seq) VALUES ('{loc}', {seq})\")\n"
        
        return inserts
    
    def _generate_balance_category_inserts(self) -> str:
        """Generate INSERT statements for balance_category enum values"""
        return '''
    # Insert balance_category enum values
    op.execute("INSERT INTO balance_category(category, seq) VALUES ('A', 1)")  # Asset
    op.execute("INSERT INTO balance_category(category, seq) VALUES ('B', 2)")  # Liability
'''
    
    def _generate_zksynclite_type_inserts(self) -> str:
        """Generate INSERT statements for zksynclite_tx_type enum values"""
        inserts = "\n    # Insert zksynclite_tx_type enum values\n"
        
        # Extract from schema.py
        zksync_sql = schema.DB_CREATE_ZKSYNCLITE_TX_TYPE
        insert_matches = re.findall(r"INSERT OR IGNORE INTO zksynclite_tx_type\(type, seq\) VALUES \('(.)', (\d+)\);", zksync_sql)
        
        for tx_type, seq in insert_matches:
            inserts += f"    op.execute(\"INSERT INTO zksynclite_tx_type(type, seq) VALUES ('{tx_type}', {seq})\")\n"
        
        return inserts


def main():
    """Generate and save the initial migration"""
    generator = MigrationGenerator()
    migration_content = generator.generate_migration_content()
    
    # Save to versions directory
    versions_dir = Path(__file__).parent / "versions"
    versions_dir.mkdir(exist_ok=True)
    
    migration_file = versions_dir / "001_initial_v48.py"
    migration_file.write_text(migration_content)
    
    print(f"Generated initial migration: {migration_file}")
    print("\nNext steps:")
    print("1. Review the generated migration file")
    print("2. Test it by running: alembic upgrade head")
    print("3. Port the remaining upgrade scripts (v26-v48)")


if __name__ == '__main__':
    main()