"""Alembic migration manager for the user database

This module provides integration between Alembic and the existing rotkehlchen
database upgrade system.
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AlembicManager:
    """Manages Alembic migrations for the user database"""
    
    def __init__(self, db: 'DBHandler'):
        self.db = db
        self.alembic_cfg_path = Path(__file__).parent.parent / 'alembic.ini'
        self.alembic_cfg = None
        self._setup_config()
    
    def _setup_config(self) -> None:
        """Setup Alembic configuration"""
        if not self.alembic_cfg_path.exists():
            raise DBUpgradeError(f"Alembic configuration not found at {self.alembic_cfg_path}")
        
        self.alembic_cfg = Config(str(self.alembic_cfg_path))
        
        # Set the database path in environment for the env.py script
        os.environ['ROTKEHLCHEN_DB_PATH'] = str(self.db.user_data_dir / 'rotkehlchen.db')
        if hasattr(self.db, 'password') and self.db.password and isinstance(self.db.password, str):
            os.environ['ROTKEHLCHEN_DB_PASSWORD'] = self.db.password
    
    def get_current_revision(self) -> Optional[str]:
        """Get the current Alembic revision from the database"""
        engine = create_engine(f"sqlite:///{self.db.user_data_dir / 'rotkehlchen.db'}")
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    
    def get_head_revision(self) -> Optional[str]:
        """Get the latest available revision"""
        script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        head = script_dir.get_current_head()
        return head
    
    def needs_migration(self) -> bool:
        """Check if the database needs migration"""
        current = self.get_current_revision()
        head = self.get_head_revision()
        return current != head
    
    def run_migrations(self, progress_handler: Optional['DBUpgradeProgressHandler'] = None) -> None:
        """Run pending migrations
        
        Args:
            progress_handler: Optional progress handler for UI updates
        """
        if not self.needs_migration():
            log.info("Database is already at the latest migration")
            return
        
        current = self.get_current_revision()
        head = self.get_head_revision()
        
        log.info(f"Running migrations from {current} to {head}")
        
        if progress_handler:
            progress_handler.new_step(f"Running Alembic migrations to {head}")
        
        try:
            command.upgrade(self.alembic_cfg, "head")
            log.info("Migrations completed successfully")
        except Exception as e:
            log.error(f"Migration failed: {e}")
            raise DBUpgradeError(f"Failed to run Alembic migrations: {e}") from e
    
    def create_migration(self, message: str, autogenerate: bool = True) -> str:
        """Create a new migration
        
        Args:
            message: Description of the migration
            autogenerate: Whether to autogenerate based on model changes
            
        Returns:
            Path to the created migration file
        """
        if autogenerate:
            command.revision(self.alembic_cfg, message=message, autogenerate=True)
        else:
            command.revision(self.alembic_cfg, message=message)
        
        # Get the newly created revision
        script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        head = script_dir.get_current_head()
        
        return str(script_dir.get_revision(head).path)
    
    def stamp_database(self, revision: str = "head") -> None:
        """Stamp the database with a specific revision without running migrations
        
        This is useful when transitioning from the old upgrade system to Alembic.
        
        Args:
            revision: The revision to stamp (default: "head")
        """
        command.stamp(self.alembic_cfg, revision)
        log.info(f"Database stamped with revision: {revision}")
    
    def get_revision_for_db_version(self, db_version: int) -> str:
        """Map a rotkehlchen DB version to an Alembic revision
        
        Args:
            db_version: The rotkehlchen database version number
            
        Returns:
            The corresponding Alembic revision ID
        """
        # This maps the old version numbers to Alembic revisions
        version_mapping = {
            48: "047_v47_to_v48",  # Current version
            47: "046_v46_to_v47",
            46: "045_v45_to_v46",
            # ... add all versions back to 26
            26: "001_initial_v48",  # Base migration
        }
        
        return version_mapping.get(db_version, "head")
    
    def transition_to_alembic(self) -> None:
        """Transition an existing database to use Alembic
        
        This stamps the database with the appropriate revision based on
        the current rotkehlchen version number.
        """
        with self.db.conn.read_ctx() as cursor:
            current_version = self.db.get_setting(cursor, 'version')
        
        if current_version != ROTKEHLCHEN_DB_VERSION:
            raise DBUpgradeError(
                f"Database must be at version {ROTKEHLCHEN_DB_VERSION} before "
                f"transitioning to Alembic. Current version: {current_version}"
            )
        
        # Check if already using Alembic
        current_revision = self.get_current_revision()
        if current_revision:
            log.info(f"Database already using Alembic (revision: {current_revision})")
            return
        
        # Stamp with the appropriate revision
        revision = self.get_revision_for_db_version(current_version)
        self.stamp_database(revision)
        
        log.info(f"Database transitioned to Alembic at revision: {revision}")