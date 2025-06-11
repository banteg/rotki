#!/usr/bin/env python3
"""Check ORM migration status by comparing tables in schema files with ORM models"""

import re
from pathlib import Path

def extract_tables_from_schema(schema_file):
    """Extract table names from SQL schema file"""
    with open(schema_file) as f:
        content = f.read()
    
    # Find all CREATE TABLE statements
    tables = set()
    pattern = r'CREATE TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)'
    matches = re.findall(pattern, content, re.IGNORECASE)
    tables.update(matches)
    
    return tables

def extract_models_from_orm(orm_dir):
    """Extract model names from ORM model files"""
    models = {}
    
    # Check all model files
    model_files = [
        'models.py',
        'user_db_models.py', 
        'global_db_models.py',
        'transient_db_models.py',
        'protocols.py',
        'enums.py',
        'eth2.py',
        'history_events.py',
        'nfts.py',
        'transactions.py',
        'zksync.py'
    ]
    
    for model_file in model_files:
        filepath = orm_dir / model_file
        if not filepath.exists():
            continue
            
        with open(filepath) as f:
            content = f.read()
        
        # Find all class definitions with __tablename__
        class_pattern = r'class\s+(\w+)\(.*?\):'
        table_pattern = r'__tablename__\s*=\s*[\'"](\w+)[\'"]'
        
        classes = re.findall(class_pattern, content)
        
        # For each class, find its tablename
        for i, match in enumerate(re.finditer(class_pattern, content)):
            class_name = match.group(1)
            # Look for __tablename__ after this class
            remaining_content = content[match.end():]
            table_match = re.search(table_pattern, remaining_content)
            if table_match:
                # Check if this tablename is before the next class
                next_class = re.search(class_pattern, remaining_content)
                if not next_class or table_match.start() < next_class.start():
                    models[table_match.group(1)] = {
                        'class': class_name,
                        'file': model_file
                    }
    
    return models

def main():
    # Paths
    schema_file = Path('/workspace/rotkehlchen/db/schema.py')
    schema_transient_file = Path('/workspace/rotkehlchen/db/schema_transient.py')
    globaldb_schema_file = Path('/workspace/rotkehlchen/globaldb/schema.py')
    orm_dir = Path('/workspace/rotkehlchen/db/orm')
    
    # Extract tables from schema files
    user_tables = extract_tables_from_schema(schema_file)
    transient_tables = extract_tables_from_schema(schema_transient_file) if schema_transient_file.exists() else set()
    global_tables = extract_tables_from_schema(globaldb_schema_file) if globaldb_schema_file.exists() else set()
    
    # Extract models from ORM
    orm_models = extract_models_from_orm(orm_dir)
    orm_tables = set(orm_models.keys())
    
    # Analysis
    print("=== ORM MIGRATION STATUS ===\n")
    
    # User DB tables
    print(f"USER DATABASE TABLES ({len(user_tables)} total):")
    print("-" * 50)
    
    user_migrated = user_tables & orm_tables
    user_not_migrated = user_tables - orm_tables
    
    print(f"✅ Migrated ({len(user_migrated)}):")
    for table in sorted(user_migrated):
        print(f"   - {table} -> {orm_models[table]['class']} ({orm_models[table]['file']})")
    
    print(f"\n❌ Not migrated ({len(user_not_migrated)}):")
    for table in sorted(user_not_migrated):
        print(f"   - {table}")
    
    # Transient DB tables
    if transient_tables:
        print(f"\n\nTRANSIENT DATABASE TABLES ({len(transient_tables)} total):")
        print("-" * 50)
        
        transient_migrated = transient_tables & orm_tables
        transient_not_migrated = transient_tables - orm_tables
        
        print(f"✅ Migrated ({len(transient_migrated)}):")
        for table in sorted(transient_migrated):
            print(f"   - {table} -> {orm_models[table]['class']} ({orm_models[table]['file']})")
        
        print(f"\n❌ Not migrated ({len(transient_not_migrated)}):")
        for table in sorted(transient_not_migrated):
            print(f"   - {table}")
    
    # Global DB tables
    if global_tables:
        print(f"\n\nGLOBAL DATABASE TABLES ({len(global_tables)} total):")
        print("-" * 50)
        
        global_migrated = global_tables & orm_tables
        global_not_migrated = global_tables - orm_tables
        
        print(f"✅ Migrated ({len(global_migrated)}):")
        for table in sorted(global_migrated):
            print(f"   - {table} -> {orm_models[table]['class']} ({orm_models[table]['file']})")
        
        print(f"\n❌ Not migrated ({len(global_not_migrated)}):")
        for table in sorted(global_not_migrated):
            print(f"   - {table}")
    
    # Summary
    all_tables = user_tables | transient_tables | global_tables
    all_migrated = all_tables & orm_tables
    
    print(f"\n\n=== SUMMARY ===")
    print(f"Total tables: {len(all_tables)}")
    print(f"Migrated: {len(all_migrated)} ({len(all_migrated)/len(all_tables)*100:.1f}%)")
    print(f"Not migrated: {len(all_tables - all_migrated)} ({len(all_tables - all_migrated)/len(all_tables)*100:.1f}%)")
    
    # Check for models without corresponding schema tables
    extra_models = orm_tables - all_tables
    if extra_models:
        print(f"\n\n⚠️  WARNING: Models without schema tables ({len(extra_models)}):")
        for table in sorted(extra_models):
            print(f"   - {table} -> {orm_models[table]['class']} ({orm_models[table]['file']})")

if __name__ == '__main__':
    main()