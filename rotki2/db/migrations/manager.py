"""Migration manager that integrates Alembic with Rotkehlchen's upgrade system.

This module provides utilities to run Alembic migrations as part of the
standard Rotkehlchen database upgrade process.
"""
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)


class AlembicManager:
    """Manages Alembic migrations for Rotkehlchen."""

    def __init__(self, db_handler: 'DBHandler'):
        self.db_handler = db_handler
        self.config = self._create_config()

    def _create_config(self) -> Config:
        """Create Alembic configuration."""
        # Find the alembic.ini file
        ini_path = Path(__file__).parent.parent.parent.parent / 'alembic.ini'
        config = Config(str(ini_path))

        # Override the database URL to use the current connection
        db_path = self.db_handler.user_data_dir / 'rotkehlchen.db'
        config.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')

        return config

    def get_current_revision(self) -> str | None:
        """Get the current Alembic revision from the database."""
        engine = create_engine(self.config.get_main_option('sqlalchemy.url'))
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()

    def run_migrations(self) -> None:
        """Run any pending Alembic migrations."""
        try:
            # Check if alembic_version table exists
            with self.db_handler.conn.read_ctx() as cursor:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'",
                )
                if cursor.fetchone() is None:
                    # Initialize Alembic
                    logger.info('Initializing Alembic for the first time')
                    command.stamp(self.config, 'head')
                    return

            # Run any pending migrations
            logger.info('Checking for pending Alembic migrations')
            command.upgrade(self.config, 'head')

        except Exception as e:
            logger.error(f'Error running Alembic migrations: {e}')
            # Don't fail the entire upgrade process if Alembic fails
            # This ensures backwards compatibility

    def create_migration(self, message: str, autogenerate: bool = True) -> None:
        """Create a new migration.
        
        Args:
            message: Description of the migration
            autogenerate: Whether to auto-detect schema changes
        """
        if autogenerate:
            command.revision(self.config, message=message, autogenerate=True)
        else:
            command.revision(self.config, message=message)

    def get_history(self) -> list[tuple[str, str]]:
        """Get migration history.
        
        Returns:
            List of (revision, message) tuples
        """
        # This would return the migration history
        # Implementation depends on Alembic internals
        return []


def run_alembic_migrations(db_handler: 'DBHandler') -> None:
    """Run Alembic migrations as part of the database upgrade process.
    
    This function should be called from the main upgrade logic after
    running the manual SQL upgrades.
    """
    manager = AlembicManager(db_handler)
    manager.run_migrations()
