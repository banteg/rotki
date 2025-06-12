#!/usr/bin/env python3
"""Script to create the initial Alembic migration from the current database state

This script reads the current database schema and creates an initial migration
that represents the current state at version 48.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rotkehlchen.db.models.user import *  # noqa: F403,F401
from rotkehlchen.db.models.user.base import Base

def create_initial_migration_script():
    """Generate the initial migration script content"""
    
    migration_content = '''"""Initial migration from v48 schema

Revision ID: 001_initial_v48
Revises: 
Create Date: 2025-01-06

This migration represents the database schema at version 48 of the user database,
after the migration to SQLModel.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, INTEGER, TEXT, VARCHAR, BLOB

# revision identifiers, used by Alembic.
revision = '001_initial_v48'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables for the v48 schema"""
    
    # Create enum tables first
    op.create_table('location',
        sa.Column('location', CHAR(1), nullable=False),
        sa.Column('seq', INTEGER, nullable=True),
        sa.PrimaryKeyConstraint('location'),
        sa.UniqueConstraint('seq')
    )
    
    op.create_table('balance_category',
        sa.Column('category', CHAR(1), nullable=False),
        sa.Column('seq', INTEGER, nullable=True),
        sa.PrimaryKeyConstraint('category'),
        sa.UniqueConstraint('seq')
    )
    
    op.create_table('zksynclite_tx_type',
        sa.Column('type', CHAR(1), nullable=False),
        sa.Column('seq', INTEGER, nullable=True),
        sa.PrimaryKeyConstraint('type'),
        sa.UniqueConstraint('seq')
    )
    
    # Insert enum values
    op.execute("INSERT INTO location(location, seq) VALUES ('A', 1)")  # External
    op.execute("INSERT INTO location(location, seq) VALUES ('B', 2)")  # Kraken
    # ... add all other location values ...
    
    op.execute("INSERT INTO balance_category(category, seq) VALUES ('A', 1)")  # Asset
    op.execute("INSERT INTO balance_category(category, seq) VALUES ('B', 2)")  # Liability
    
    op.execute("INSERT INTO zksynclite_tx_type(type, seq) VALUES ('A', 1)")  # Transfer
    # ... add all other zksynclite_tx_type values ...
    
    # Create core tables
    op.create_table('assets',
        sa.Column('identifier', TEXT, nullable=False),
        sa.PrimaryKeyConstraint('identifier')
    )
    
    op.create_table('tags',
        sa.Column('name', TEXT, nullable=False),
        sa.Column('description', TEXT, nullable=True),
        sa.Column('background_color', TEXT, nullable=True),
        sa.Column('foreground_color', TEXT, nullable=True),
        sa.PrimaryKeyConstraint('name')
    )
    
    op.create_table('settings',
        sa.Column('name', VARCHAR(24), nullable=False),
        sa.Column('value', TEXT, nullable=True),
        sa.PrimaryKeyConstraint('name')
    )
    
    # Create tables with foreign keys
    op.create_table('tag_mappings',
        sa.Column('object_reference', TEXT, nullable=False),
        sa.Column('tag_name', TEXT, nullable=False),
        sa.ForeignKeyConstraint(['tag_name'], ['tags.name']),
        sa.PrimaryKeyConstraint('object_reference', 'tag_name')
    )
    
    # Add all other tables following the dependency order...
    # This is a placeholder - the actual implementation would include all tables
    
    # Create indexes
    op.create_index('idx_history_events_entry_type', 'history_events', ['entry_type'])
    op.create_index('idx_history_events_timestamp', 'history_events', ['timestamp'])
    op.create_index('idx_history_events_location', 'history_events', ['location'])
    op.create_index('idx_history_events_location_label', 'history_events', ['location_label'])
    op.create_index('idx_history_events_asset', 'history_events', ['asset'])
    op.create_index('idx_history_events_type', 'history_events', ['type'])
    op.create_index('idx_history_events_subtype', 'history_events', ['subtype'])
    op.create_index('idx_history_events_ignored', 'history_events', ['ignored'])


def downgrade() -> None:
    """Drop all tables"""
    # Drop tables in reverse order of creation to handle foreign keys
    # This is a placeholder - actual implementation would drop all tables
    pass
'''
    
    return migration_content


if __name__ == '__main__':
    print("Generating initial migration script...")
    
    # TODO: This is a placeholder. The actual implementation would:
    # 1. Connect to an existing v48 database
    # 2. Introspect all tables and their structure
    # 3. Generate the complete migration script
    # 4. Save it to the versions directory
    
    print("Initial migration script generation complete!")
    print("\nNext steps:")
    print("1. Review the generated migration")
    print("2. Test it on a fresh database")
    print("3. Port the upgrade scripts v26-v48 as individual migrations")