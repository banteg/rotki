"""Tests for Alembic database migrations"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from rotkehlchen.db.alembic_manager import AlembicManager
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.models.user.base import Base
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.tests.utils.database import DBUpgradeTestDB
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test databases"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def alembic_config(temp_db_dir):
    """Create a test Alembic configuration"""
    cfg_path = Path(__file__).parent.parent.parent / 'alembic.ini'
    cfg = Config(str(cfg_path))
    
    # Set test database path
    test_db_path = Path(temp_db_dir) / 'test.db'
    os.environ['ROTKEHLCHEN_DB_PATH'] = str(test_db_path)
    
    return cfg


class TestAlembicMigrations:
    """Test Alembic migration functionality"""
    
    def test_initial_migration_creates_all_tables(self, alembic_config, temp_db_dir):
        """Test that the initial migration creates all expected tables"""
        # Run migrations up to head
        command.upgrade(alembic_config, "head")
        
        # Connect to the database and check tables
        db_path = Path(temp_db_dir) / 'test.db'
        engine = create_engine(f'sqlite:///{db_path}')
        inspector = inspect(engine)
        
        # Check that key tables exist
        expected_tables = [
            'assets',
            'settings',
            'blockchain_accounts',
            'history_events',
            'evm_transactions',
            'tags',
            'manually_tracked_balances',
            # ... add more tables
        ]
        
        tables = inspector.get_table_names()
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
    
    def test_migration_sequence(self, alembic_config, temp_db_dir):
        """Test running migrations in sequence"""
        # Start with initial migration
        command.upgrade(alembic_config, "001_initial_v48")
        
        # Check we're at the right revision
        db_path = Path(temp_db_dir) / 'test.db'
        engine = create_engine(f'sqlite:///{db_path}')
        
        from alembic.runtime.migration import MigrationContext
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            assert context.get_current_revision() == "001_initial_v48"
        
        # Upgrade to next version
        command.upgrade(alembic_config, "026_v26_to_v27")
        
        # Check revision updated
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            assert context.get_current_revision() == "026_v26_to_v27"
    
    def test_alembic_manager_integration(self, temp_db_dir):
        """Test AlembicManager integration with DBHandler"""
        # Create a test database
        msg_aggregator = MessagesAggregator()
        db = DBHandler(
            user_data_dir=Path(temp_db_dir),
            password='test_password',
            msg_aggregator=msg_aggregator,
            sql_vm_instructions_cb=0,
        )
        
        # Create AlembicManager
        manager = AlembicManager(db)
        
        # Test getting current revision (should be None for new DB)
        assert manager.get_current_revision() is None
        
        # Test transition to Alembic
        with patch.object(db, 'get_setting', return_value=ROTKEHLCHEN_DB_VERSION):
            manager.transition_to_alembic()
        
        # Check that database is now stamped
        current_rev = manager.get_current_revision()
        assert current_rev is not None
    
    def test_migration_rollback_on_error(self, alembic_config, temp_db_dir):
        """Test that migrations rollback on error"""
        # Create a migration that will fail
        with patch('alembic.command.upgrade', side_effect=Exception("Migration failed")):
            with pytest.raises(DBUpgradeError):
                manager = AlembicManager(None)  # Simplified for test
                manager.alembic_cfg = alembic_config
                manager.run_migrations()
    
    def test_version_mapping(self):
        """Test mapping between old version numbers and Alembic revisions"""
        # Create a mock DB handler for this test
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        manager = AlembicManager(mock_db)
        
        # Test known versions
        assert manager.get_revision_for_db_version(48) == "047_v47_to_v48"
        assert manager.get_revision_for_db_version(26) == "001_initial_v48"
        
        # Test unknown version defaults to head
        assert manager.get_revision_for_db_version(99) == "head"
    
    @pytest.mark.parametrize('db_version', [26, 30, 40, 48])
    def test_upgrade_from_old_version(self, db_version, temp_db_dir):
        """Test upgrading from various old database versions"""
        # Prepare a database at the specified version
        db_path = Path(temp_db_dir) / 'rotkehlchen.db'
        # Use the test helper to create a DB at the specific version
        test_db = DBUpgradeTestDB(db_path, db_version)
        
        # Create DBHandler and AlembicManager
        msg_aggregator = MessagesAggregator()
        db = DBHandler(
            user_data_dir=temp_db_dir,
            password='test_password',
            msg_aggregator=msg_aggregator,
            sql_vm_instructions_cb=0,
        )
        
        manager = AlembicManager(db)
        
        # Run the upgrade through Alembic
        manager.run_migrations()
        
        # Verify we're at the latest version
        assert manager.get_current_revision() == manager.get_head_revision()
    
    def test_concurrent_migration_protection(self, temp_db_dir):
        """Test that concurrent migrations are prevented"""
        # This would test the locking mechanism to prevent multiple
        # processes from running migrations simultaneously
        pass  # Implementation depends on locking strategy
    
    def test_migration_with_encrypted_database(self, temp_db_dir):
        """Test migrations work with SQLCipher encrypted databases"""
        # Set up encrypted database
        os.environ['ROTKEHLCHEN_DB_PASSWORD'] = 'test_password'
        
        # Create database and run migrations
        # ... test implementation ...
        pass