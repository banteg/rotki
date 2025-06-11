"""Helper utilities for Alembic migrations in Rotkehlchen"""

import os
import subprocess
from pathlib import Path
from typing import Optional


class AlembicHelper:
    """Helper class for managing Alembic migrations"""
    
    def __init__(self, db_type: str, db_path: Optional[Path] = None, password: Optional[str] = None):
        """
        Initialize Alembic helper
        
        Args:
            db_type: Type of database ('user', 'global', 'transient')
            db_path: Path to the database file
            password: Password for encrypted databases (user DB)
        """
        self.db_type = db_type
        self.db_path = db_path
        self.password = password
        self.alembic_dir = Path(__file__).parent / 'alembic'
        
    def get_db_url(self) -> str:
        """Get the database URL for Alembic"""
        if self.db_path is None:
            raise ValueError("Database path not provided")
        
        if self.db_type == 'user' and self.password:
            # SQLCipher URL for encrypted database
            return f"sqlite+pysqlcipher://:{self.password}@/{self.db_path}"
        else:
            # Regular SQLite URL
            return f"sqlite:///{self.db_path}"
    
    def run_command(self, command: list[str]) -> subprocess.CompletedProcess:
        """Run an Alembic command"""
        env = os.environ.copy()
        
        # Add database URL to command
        db_url = self.get_db_url()
        command.extend(['-x', f'db_url={db_url}'])
        
        # Change to alembic directory
        original_cwd = os.getcwd()
        try:
            os.chdir(self.alembic_dir)
            result = subprocess.run(
                ['alembic'] + command,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                print(f"Error running Alembic command: {result.stderr}")
            return result
        finally:
            os.chdir(original_cwd)
    
    def init_db(self) -> None:
        """Initialize database with current schema"""
        self.run_command(['stamp', 'head'])
    
    def create_migration(self, message: str) -> subprocess.CompletedProcess:
        """Create a new migration"""
        return self.run_command(['revision', '--autogenerate', '-m', message])
    
    def upgrade(self, revision: str = 'head') -> subprocess.CompletedProcess:
        """Upgrade database to a revision"""
        return self.run_command(['upgrade', revision])
    
    def downgrade(self, revision: str) -> subprocess.CompletedProcess:
        """Downgrade database to a revision"""
        return self.run_command(['downgrade', revision])
    
    def current(self) -> subprocess.CompletedProcess:
        """Show current revision"""
        return self.run_command(['current'])
    
    def history(self) -> subprocess.CompletedProcess:
        """Show migration history"""
        return self.run_command(['history'])


# Example usage:
if __name__ == '__main__':
    # Example for user database
    helper = AlembicHelper(
        db_type='user',
        db_path=Path('/path/to/rotkehlchen.db'),
        password='your_password'
    )
    
    # Initialize database with current schema
    helper.init_db()
    
    # Create a new migration
    helper.create_migration("Add new feature")
    
    # Upgrade to latest
    helper.upgrade()