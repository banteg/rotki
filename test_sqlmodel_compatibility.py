#!/usr/bin/env python3
"""Test SQLModel compatibility with existing SQLAlchemy models"""

import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy import create_engine

# Import SQLAlchemy models
from rotkehlchen.db.orm.base import UserDBBase as SQLAlchemyUserBase
from rotkehlchen.db.orm.enums import Location as SQLAlchemyLocation
from rotkehlchen.db.orm.models import Asset as SQLAlchemyAsset

# Import SQLModel models  
from rotkehlchen.db.orm.base_sqlmodel import UserDBBase as SQLModelUserBase
from rotkehlchen.db.orm.enums_sqlmodel import Location as SQLModelLocation
from rotkehlchen.db.orm.models_sqlmodel import Asset as SQLModelAsset


def get_table_columns(conn, table_name):
    """Get column information for a table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info('{table_name}')")
    columns = {}
    for row in cursor.fetchall():
        columns[row[1]] = {
            'type': row[2],
            'notnull': bool(row[3]),
            'default': row[4],
            'pk': row[5]
        }
    return columns


def test_model_compatibility():
    """Test that SQLModel generates same schema as SQLAlchemy"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create SQLAlchemy database
        sqlalchemy_db_path = tmppath / "sqlalchemy.db"
        sqlalchemy_engine = create_engine(f"sqlite:///{sqlalchemy_db_path}")
        
        # Create only specific tables to test
        SQLAlchemyLocation.__table__.create(sqlalchemy_engine)
        SQLAlchemyAsset.__table__.create(sqlalchemy_engine)
        
        # Create SQLModel database
        sqlmodel_db_path = tmppath / "sqlmodel.db"
        sqlmodel_engine = create_engine(f"sqlite:///{sqlmodel_db_path}")
        
        # Create same tables with SQLModel
        SQLModelLocation.__table__.create(sqlmodel_engine)
        SQLModelAsset.__table__.create(sqlmodel_engine)
        
        # Compare schemas
        sqlalchemy_conn = sqlite3.connect(str(sqlalchemy_db_path))
        sqlmodel_conn = sqlite3.connect(str(sqlmodel_db_path))
        
        tables_to_test = ['location', 'assets']
        
        for table in tables_to_test:
            sqlalchemy_cols = get_table_columns(sqlalchemy_conn, table)
            sqlmodel_cols = get_table_columns(sqlmodel_conn, table)
            
            print(f"\n{table} table:")
            print(f"  SQLAlchemy: {sqlalchemy_cols}")
            print(f"  SQLModel:   {sqlmodel_cols}")
            print(f"  Match: {sqlalchemy_cols == sqlmodel_cols}")
            
        sqlalchemy_conn.close()
        sqlmodel_conn.close()


if __name__ == "__main__":
    test_model_compatibility()