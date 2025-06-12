"""Integration tests for Alembic migration system

These tests verify that the Alembic migration system works correctly
with the existing rotkehlchen database.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.db.alembic_manager import AlembicManager
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.user_messages import MessagesAggregator


class TestAlembicIntegration:
    """Test Alembic integration with rotkehlchen"""
    
    def test_alembic_manager_creation(self):
        """Test that AlembicManager can be created"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        mock_db.password = None
        
        manager = AlembicManager(mock_db)
        assert manager.db == mock_db
        assert manager.alembic_cfg is not None
    
    def test_version_mapping(self):
        """Test mapping between old version numbers and Alembic revisions"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        manager = AlembicManager(mock_db)
        
        # Test known versions
        assert manager.get_revision_for_db_version(48) == "047_v47_to_v48"
        assert manager.get_revision_for_db_version(26) == "001_initial_v48"
        
        # Test unknown version defaults to head
        assert manager.get_revision_for_db_version(99) == "head"
    
    @patch('rotkehlchen.db.alembic_manager.create_engine')
    @patch('rotkehlchen.db.alembic_manager.MigrationContext')
    def test_get_current_revision(self, mock_context, mock_engine):
        """Test getting current revision from database"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        manager = AlembicManager(mock_db)
        
        # Mock the context to return a revision
        mock_ctx_instance = MagicMock()
        mock_ctx_instance.get_current_revision.return_value = "001_initial_v48"
        mock_context.configure.return_value = mock_ctx_instance
        
        revision = manager.get_current_revision()
        assert revision == "001_initial_v48"
    
    @patch('rotkehlchen.db.alembic_manager.ScriptDirectory')
    def test_get_head_revision(self, mock_script_dir):
        """Test getting head revision"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        manager = AlembicManager(mock_db)
        
        # Mock the script directory
        mock_script_instance = MagicMock()
        mock_script_instance.get_current_head.return_value = "047_v47_to_v48"
        mock_script_dir.from_config.return_value = mock_script_instance
        
        head = manager.get_head_revision()
        assert head == "047_v47_to_v48"
    
    def test_transition_to_alembic_requires_latest_version(self):
        """Test that transition to Alembic requires DB to be at latest version"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        mock_db.conn = MagicMock()
        mock_db.get_setting = MagicMock(return_value=47)  # Old version
        
        manager = AlembicManager(mock_db)
        
        with pytest.raises(DBUpgradeError, match="must be at version"):
            manager.transition_to_alembic()
    
    @patch('rotkehlchen.db.alembic_manager.command')
    def test_stamp_database(self, mock_command):
        """Test stamping database with revision"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        manager = AlembicManager(mock_db)
        
        manager.stamp_database("001_initial_v48")
        
        mock_command.stamp.assert_called_once_with(
            manager.alembic_cfg,
            "001_initial_v48"
        )
    
    @patch('rotkehlchen.db.alembic_manager.command')
    @patch('rotkehlchen.db.alembic_manager.create_engine')
    @patch('rotkehlchen.db.alembic_manager.MigrationContext')
    def test_transition_to_alembic_success(self, mock_context, mock_engine, mock_command):
        """Test successful transition to Alembic"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        mock_db.conn = MagicMock()
        mock_db.get_setting = MagicMock(return_value=ROTKEHLCHEN_DB_VERSION)
        
        # Mock no current revision (not using Alembic yet)
        mock_ctx_instance = MagicMock()
        mock_ctx_instance.get_current_revision.return_value = None
        mock_context.configure.return_value = mock_ctx_instance
        
        manager = AlembicManager(mock_db)
        manager.transition_to_alembic()
        
        # Should stamp with appropriate revision
        expected_revision = manager.get_revision_for_db_version(ROTKEHLCHEN_DB_VERSION)
        mock_command.stamp.assert_called_once_with(
            manager.alembic_cfg,
            expected_revision
        )
    
    @patch('rotkehlchen.db.alembic_manager.command')
    @patch('rotkehlchen.db.alembic_manager.ScriptDirectory')
    @patch('rotkehlchen.db.alembic_manager.create_engine')
    @patch('rotkehlchen.db.alembic_manager.MigrationContext')
    def test_run_migrations(self, mock_context, mock_engine, mock_script_dir, mock_command):
        """Test running migrations"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        manager = AlembicManager(mock_db)
        
        # Mock current revision != head
        mock_ctx_instance = MagicMock()
        mock_ctx_instance.get_current_revision.return_value = "001_initial_v48"
        mock_context.configure.return_value = mock_ctx_instance
        
        mock_script_instance = MagicMock()
        mock_script_instance.get_current_head.return_value = "047_v47_to_v48"
        mock_script_dir.from_config.return_value = mock_script_instance
        
        # Run migrations
        manager.run_migrations()
        
        # Should call upgrade to head
        mock_command.upgrade.assert_called_once_with(
            manager.alembic_cfg,
            "head"
        )
    
    @patch('rotkehlchen.db.alembic_manager.command')
    @patch('rotkehlchen.db.alembic_manager.ScriptDirectory')
    @patch('rotkehlchen.db.alembic_manager.create_engine')
    @patch('rotkehlchen.db.alembic_manager.MigrationContext')
    def test_no_migration_needed(self, mock_context, mock_engine, mock_script_dir, mock_command):
        """Test when no migration is needed"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        manager = AlembicManager(mock_db)
        
        # Mock current revision == head
        mock_ctx_instance = MagicMock()
        mock_ctx_instance.get_current_revision.return_value = "047_v47_to_v48"
        mock_context.configure.return_value = mock_ctx_instance
        
        mock_script_instance = MagicMock()
        mock_script_instance.get_current_head.return_value = "047_v47_to_v48"
        mock_script_dir.from_config.return_value = mock_script_instance
        
        # Run migrations
        manager.run_migrations()
        
        # Should not call upgrade
        mock_command.upgrade.assert_not_called()
    
    def test_alembic_config_missing(self):
        """Test error when Alembic config is missing"""
        mock_db = MagicMock()
        mock_db.user_data_dir = Path('/tmp')
        
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(DBUpgradeError, match="Alembic configuration not found"):
                AlembicManager(mock_db)