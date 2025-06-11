"""Database migration framework for transitioning to ORM"""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from rotkehlchen.db.orm.database import RotkehlchenDatabase
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = RotkehlchenLogsAdapter(__name__)


@dataclass
class MigrationStep:
    """Represents a single migration step"""
    name: str
    description: str
    migrate_func: Callable[[Session, Session], None]
    verify_func: Callable[[Session, Session], bool] | None = None
    rollback_func: Callable[[Session, Session], None] | None = None


class DatabaseMigrator:
    """
    Manages migration from old raw SQL database to new ORM.

    This class provides a framework for gradually migrating
    data from the old schema to the new ORM-based schema.
    """

    def __init__(
        self,
        old_db_path: Path,
        new_db: RotkehlchenDatabase,
        batch_size: int = 1000,
    ):
        """
        Initialize migrator.

        Args:
            old_db_path: Path to old database
            new_db: New ORM database instance
            batch_size: Batch size for bulk operations
        """
        self.old_db_path = old_db_path
        self.new_db = new_db
        self.batch_size = batch_size
        self.steps: list[MigrationStep] = []

        # Create connection to old database
        from rotkehlchen.db.dbhandler import DBHandler
        self.old_db = DBHandler(
            user_data_dir=old_db_path.parent,
            password=new_db.password,
            initial_settings=None,
        )

    def add_step(self, step: MigrationStep) -> None:
        """Add a migration step"""
        self.steps.append(step)
        logger.debug(f'Added migration step: {step.name}')

    def migrate(self, verify: bool = True) -> None:
        """
        Run all migration steps.

        Args:
            verify: Whether to verify each step
        """
        logger.info(f'Starting database migration with {len(self.steps)} steps')
        start_time = time.time()

        with self.new_db.session_manager.user_db_session(commit=False) as new_session:
            for i, step in enumerate(self.steps, 1):
                logger.info(f'[{i}/{len(self.steps)}] Running migration: {step.name}')

                try:
                    # Run migration
                    step.migrate_func(self.old_db.conn, new_session)

                    # Verify if requested
                    if verify and step.verify_func:
                        logger.debug(f'Verifying migration: {step.name}')
                        if not step.verify_func(self.old_db.conn, new_session):
                            raise RuntimeError(f'Verification failed for step: {step.name}')

                    # Commit after each step
                    new_session.commit()
                    logger.info(f'Completed migration: {step.name}')

                except Exception as e:
                    logger.error(f"Migration failed at step '{step.name}': {e}")

                    # Attempt rollback if available
                    if step.rollback_func:
                        logger.info(f'Attempting rollback for: {step.name}')
                        try:
                            step.rollback_func(self.old_db.conn, new_session)
                            new_session.commit()
                        except Exception as rollback_error:
                            logger.error(f'Rollback failed: {rollback_error}')

                    new_session.rollback()
                    raise

        elapsed = time.time() - start_time
        logger.info(f'Migration completed successfully in {elapsed:.2f} seconds')

    def migrate_table(
        self,
        table_name: str,
        mapping_func: Callable[[dict], dict],
        target_model: Any,
    ) -> None:
        """
        Generic table migration helper.

        Args:
            table_name: Source table name
            mapping_func: Function to map old row to new model data
            target_model: Target ORM model class
        """
        logger.debug(f'Migrating table: {table_name}')

        with self.new_db.session_manager.user_db_session() as session:
            # Query old data
            cursor = self.old_db.conn.cursor()
            cursor.execute(f'SELECT * FROM {table_name}')

            batch = []
            row_count = 0

            for row in cursor:
                # Convert row to dict
                row_dict = dict(row)

                # Map to new schema
                mapped_data = mapping_func(row_dict)

                # Create model instance
                instance = target_model(**mapped_data)
                batch.append(instance)

                # Bulk insert when batch is full
                if len(batch) >= self.batch_size:
                    session.bulk_save_objects(batch)
                    session.commit()
                    row_count += len(batch)
                    batch = []
                    logger.debug(f'Migrated {row_count} rows from {table_name}')

            # Insert remaining
            if batch:
                session.bulk_save_objects(batch)
                session.commit()
                row_count += len(batch)

            logger.info(f'Migrated {row_count} rows from {table_name}')

    def verify_row_count(self, old_table: str, new_model: Any) -> bool:
        """
        Verify row count matches between old and new database.

        Args:
            old_table: Old table name
            new_model: New model class

        Returns:
            True if counts match
        """
        # Get old count
        cursor = self.old_db.conn.cursor()
        old_count = cursor.execute(f'SELECT COUNT(*) FROM {old_table}').fetchone()[0]

        # Get new count
        with self.new_db.session_manager.user_db_session() as session:
            new_count = session.query(new_model).count()

        match = old_count == new_count
        if not match:
            logger.error(
                f'Row count mismatch for {old_table}: '
                f'old={old_count}, new={new_count}',
            )

        return match

    def close(self) -> None:
        """Close connections"""
        self.old_db.disconnect()


class BaseMigrationStep(ABC):
    """Base class for migration steps"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Migration step name"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Migration step description"""

    @abstractmethod
    def migrate(self, old_conn: Any, new_session: Session) -> None:
        """Run migration"""

    def verify(self, old_conn: Any, new_session: Session) -> bool:
        """Verify migration (optional)"""
        return True

    def rollback(self, old_conn: Any, new_session: Session) -> None:
        """Rollback migration (optional)"""

    def to_migration_step(self) -> MigrationStep:
        """Convert to MigrationStep"""
        return MigrationStep(
            name=self.name,
            description=self.description,
            migrate_func=self.migrate,
            verify_func=self.verify,
            rollback_func=self.rollback,
        )
