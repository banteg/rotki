"""Database initialization and management for rotkehlchen ORM"""

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from rotkehlchen.db.orm.engines import (
    create_global_db_engine,
    create_transient_db_engine,
    create_user_db_engine,
    test_engine_connection,
)
from rotkehlchen.db.orm.models import (
    TransientDBBase,
    UserDBBase,
)
from rotkehlchen.db.orm.repository_manager import (
    GlobalDBRepositoryManager,
    RepositoryManager,
    TransientDBRepositoryManager,
)
from rotkehlchen.db.orm.session import initialize_session_manager
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = RotkehlchenLogsAdapter(__name__)

# Current database versions
USERDB_VERSION = 48
GLOBALDB_VERSION = 12


class RotkehlchenDatabase:
    """
    Main database class for rotkehlchen using SQLAlchemy ORM.

    This class manages all three databases (user, global, transient)
    and provides high-level operations.
    """

    def __init__(
        self,
        user_data_dir: Path,
        password: str | None = None,
        sql_vm_instructions_cb: int | None = None,
        resume_from_backup: bool = True,
        echo_sql: bool = False,
    ):
        """
        Initialize rotkehlchen database.

        Args:
            user_data_dir: User data directory
            password: Optional password for encryption
            sql_vm_instructions_cb: SQLite VM instruction callback
            resume_from_backup: Whether to resume from backup on error
            echo_sql: Whether to echo SQL statements
        """
        self.user_data_dir = user_data_dir
        self.password = password
        self.echo_sql = echo_sql

        # Database paths
        self.user_db_path = user_data_dir / 'rotkehlchen.db'
        self.global_db_path = user_data_dir.parent / 'global' / 'global.db'

        # Ensure directories exist
        self.user_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.global_db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize session manager
        self.session_manager = initialize_session_manager(
            user_db_path=str(self.user_db_path),
            global_db_path=str(self.global_db_path),
            password=password,
            echo_sql=echo_sql,
        )

        # Initialize repository managers
        self.repos = RepositoryManager(self.session_manager.user_session)
        self.global_repos = GlobalDBRepositoryManager(self.session_manager.global_session)
        self.transient_repos = TransientDBRepositoryManager(self.session_manager.transient_session)

        # Initialize databases
        self._initialize_databases()

    def _initialize_databases(self) -> None:
        """Initialize all databases"""
        logger.info('Initializing rotkehlchen databases')

        # Initialize user database
        self._initialize_user_db()

        # Initialize global database (if not exists)
        self._initialize_global_db()

        # Initialize transient database
        self._initialize_transient_db()

        logger.info('All databases initialized successfully')

    def _initialize_user_db(self) -> None:
        """Initialize user database"""
        logger.debug(f'Initializing user database at {self.user_db_path}')

        # Check if database exists
        if self.user_db_path.exists():
            # Verify we can connect
            engine = create_user_db_engine(
                str(self.user_db_path),
                self.password,
                echo=self.echo_sql,
            )

            if not test_engine_connection(engine):
                raise OperationalError('Failed to connect to user database')

            # Check version
            with self.session_manager.user_db_session():
                db_info = self.repos.database_info.get_info()
                if db_info and db_info.version != USERDB_VERSION:
                    logger.warning(
                        f'User database version mismatch. '
                        f'Expected: {USERDB_VERSION}, Found: {db_info.version}',
                    )
                    # TODO: Run migrations

            engine.dispose()
        else:
            # Create new database
            logger.info('Creating new user database')
            self._create_user_db()

    def _create_user_db(self) -> None:
        """Create new user database with all tables"""
        engine = create_user_db_engine(
            str(self.user_db_path),
            self.password,
            echo=self.echo_sql,
        )

        try:
            # Create all tables
            UserDBBase.metadata.create_all(engine)

            # Set initial version
            with self.session_manager.user_db_session():
                self.repos.database_info.set_version(USERDB_VERSION)

            logger.info('User database created successfully')
        finally:
            engine.dispose()

    def _initialize_global_db(self) -> None:
        """Initialize global database"""
        logger.debug(f'Initializing global database at {self.global_db_path}')

        if not self.global_db_path.exists():
            # Global DB should be provided with the application
            raise FileNotFoundError(
                f'Global database not found at {self.global_db_path}. '
                'Please ensure rotkehlchen is properly installed.',
            )

        # Verify we can connect
        engine = create_global_db_engine(str(self.global_db_path), echo=self.echo_sql)

        if not test_engine_connection(engine):
            raise OperationalError('Failed to connect to global database')

        engine.dispose()

    def _initialize_transient_db(self) -> None:
        """Initialize transient (in-memory) database"""
        logger.debug('Initializing transient database')

        engine = create_transient_db_engine(echo=self.echo_sql)

        try:
            # Create all tables
            TransientDBBase.metadata.create_all(engine)
            logger.info('Transient database created successfully')
        finally:
            engine.dispose()

    def get_version(self) -> int:
        """Get user database version"""
        db_info = self.repos.database_info.get_info()
        return db_info.version if db_info else 0

    def set_version(self, version: int) -> None:
        """Set user database version"""
        self.repos.database_info.set_version(version)
        self.session_manager.user_session.commit()

    def backup(self, backup_path: Path | None = None) -> Path:
        """
        Create backup of user database.

        Args:
            backup_path: Optional custom backup path

        Returns:
            Path to backup file
        """
        if backup_path is None:
            backup_path = self.user_db_path.with_suffix('.backup.db')

        logger.info(f'Creating database backup at {backup_path}')

        # Use SQLite backup API
        with self.session_manager.user_db_session() as session:
            session.execute(text(f"VACUUM INTO '{backup_path}'"))

        logger.info('Database backup completed')
        return backup_path

    def restore(self, backup_path: Path) -> None:
        """
        Restore user database from backup.

        Args:
            backup_path: Path to backup file
        """
        logger.info(f'Restoring database from {backup_path}')

        if not backup_path.exists():
            raise FileNotFoundError(f'Backup file not found: {backup_path}')

        # Close current connections
        self.close()

        # Replace database file
        import shutil
        shutil.copy2(backup_path, self.user_db_path)

        # Reinitialize
        self.__init__(
            user_data_dir=self.user_data_dir,
            password=self.password,
            echo_sql=self.echo_sql,
        )

        logger.info('Database restored successfully')

    def close(self) -> None:
        """Close all database connections"""
        self.session_manager.close_all()
        logger.info('Database connections closed')

    def __enter__(self) -> 'RotkehlchenDatabase':
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        self.close()


def create_database(
    user_data_dir: Path,
    password: str | None = None,
    echo_sql: bool = False,
) -> RotkehlchenDatabase:
    """
    Factory function to create a rotkehlchen database.

    Args:
        user_data_dir: User data directory
        password: Optional password for encryption
        echo_sql: Whether to echo SQL statements

    Returns:
        Initialized database instance
    """
    return RotkehlchenDatabase(
        user_data_dir=user_data_dir,
        password=password,
        echo_sql=echo_sql,
    )
