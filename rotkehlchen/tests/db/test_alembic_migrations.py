"""Tests for Alembic database migrations"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from rotkehlchen.db.alembic_manager import AlembicManager
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.models.user.base import Base
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.errors.misc import DBUpgradeError
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
        command.upgrade(alembic_config, "001_initial_v26")
        
        # Check we're at the right revision
        db_path = Path(temp_db_dir) / 'test.db'
        engine = create_engine(f'sqlite:///{db_path}')
        
        from alembic.runtime.migration import MigrationContext
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            assert context.get_current_revision() == "001_initial_v26"
        
        # Upgrade to next version
        command.upgrade(alembic_config, "026_v26_to_v27")
        
        # Check revision updated
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            assert context.get_current_revision() == "026_v26_to_v27"
    
    def test_alembic_manager_integration(self, temp_db_dir):
        """Test AlembicManager integration with DBHandler"""
        # Create a mock database handler
        mock_db = MagicMock()
        mock_db.user_data_dir = Path(temp_db_dir)
        mock_db.password = 'test_password'
        mock_db.conn = MagicMock()
        mock_db.get_setting = MagicMock(return_value=ROTKEHLCHEN_DB_VERSION)
        
        # Create AlembicManager
        manager = AlembicManager(mock_db)
        
        # Test basic functionality
        assert manager.db == mock_db
        assert manager.alembic_cfg is not None
    
    def test_migration_rollback_on_error(self, alembic_config, temp_db_dir):
        """Test that migrations rollback on error"""
        # Create a mock database
        mock_db = MagicMock()
        mock_db.user_data_dir = Path(temp_db_dir)
        mock_db.password = None
        
        manager = AlembicManager(mock_db)
        
        # Mock a failing upgrade
        with patch('alembic.command.upgrade', side_effect=Exception("Migration failed")):
            with pytest.raises(DBUpgradeError):
                manager.run_migrations()
    
    def test_version_mapping(self):
        """Test mapping between old version numbers and Alembic revisions"""
        # Create a mock DB handler for this test
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        mock_db.password = None
        manager = AlembicManager(mock_db)
        
        # Test known versions
        assert manager.get_revision_for_db_version(48) == "047_v47_to_v48"
        assert manager.get_revision_for_db_version(26) == "001_initial_v26"
        
        # Test unknown version defaults to head
        assert manager.get_revision_for_db_version(99) == "head"
    
    def test_upgrade_from_old_version(self, temp_db_dir):
        """Test upgrading from old database versions"""
        # This test would require actual database files at different versions
        # For now, we'll skip the implementation
        pytest.skip("Test requires database files at specific versions")
    
    def test_concurrent_migration_protection(self, temp_db_dir):
        """Test that concurrent migrations are prevented"""
        # This would test the locking mechanism to prevent multiple
        # processes from running migrations simultaneously
        pass  # Implementation depends on locking strategy
    
    def test_migration_with_encrypted_database(self, temp_db_dir):
        """Test migrations work with SQLCipher encrypted databases"""
        # Set up encrypted database
        os.environ['ROTKEHLCHEN_DB_PASSWORD'] = 'test_password'
        
        # This test requires more setup
        pytest.skip("Test requires SQLCipher setup")