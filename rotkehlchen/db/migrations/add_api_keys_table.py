"""Database migration script to add API keys table for v2 API authentication"""
import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.utils import table_exists
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def add_api_keys_table(db: 'DBHandler') -> None:
    """Add the api_keys table if it doesn't exist
    
    This table stores API keys for v2 API authentication.
    Each user can have multiple API keys with different names and expiration dates.
    """
    with db.user_write() as write_cursor:
        if not table_exists(write_cursor, 'api_keys'):
            log.info('Creating api_keys table for v2 API authentication')
            _create_api_keys_table(write_cursor)
            log.info('Successfully created api_keys table')
        else:
            log.info('api_keys table already exists, skipping creation')


def _create_api_keys_table(write_cursor: 'DBCursor') -> None:
    """Create the api_keys table schema"""
    write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            created_at DATETIME NOT NULL,
            last_used DATETIME,
            expires_at DATETIME,
            FOREIGN KEY(username) REFERENCES user_accounts(username) ON DELETE CASCADE
        );
    """)
    
    # Create indexes for better query performance
    write_cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_keys_username 
        ON api_keys(username);
    """)
    
    write_cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash 
        ON api_keys(key_hash);
    """)
    
    write_cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at 
        ON api_keys(expires_at);
    """)


def check_and_create_user_accounts_table(db: 'DBHandler') -> None:
    """Ensure user_accounts table exists for API key foreign key reference
    
    This is needed if the database doesn't already have a user_accounts table.
    In the full implementation, this would be part of the overall user management system.
    """
    with db.user_write() as write_cursor:
        if not table_exists(write_cursor, 'user_accounts'):
            log.info('Creating user_accounts table for API key foreign key reference')
            write_cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_accounts (
                    username VARCHAR(255) PRIMARY KEY NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    last_login DATETIME
                );
            """)
            log.info('Successfully created user_accounts table')


def run_migration(db: 'DBHandler') -> None:
    """Run the full migration to add API keys support
    
    This is the main entry point for the migration script.
    It ensures all necessary tables and indexes are created.
    """
    log.info('Starting API keys table migration')
    
    try:
        # First ensure user_accounts table exists
        check_and_create_user_accounts_table(db)
        
        # Then create the api_keys table
        add_api_keys_table(db)
        
        log.info('API keys table migration completed successfully')
        
    except Exception as e:
        log.error(f'Failed to run API keys table migration: {e}')
        raise


# Utility functions for working with API keys

def create_api_key(
    db: 'DBHandler',
    username: str,
    key_hash: str,
    name: str,
    expires_at: str | None = None,
) -> int:
    """Create a new API key for a user
    
    Args:
        db: Database handler
        username: Username the key belongs to
        key_hash: Hashed API key (should be hashed with appropriate algorithm)
        name: Human-readable name for the API key
        expires_at: Optional expiration datetime in ISO format
    
    Returns:
        The ID of the created API key
    """
    from datetime import datetime
    
    with db.user_write() as write_cursor:
        write_cursor.execute("""
            INSERT INTO api_keys (username, key_hash, name, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            username,
            key_hash,
            name,
            datetime.now().isoformat(),
            expires_at,
        ))
        return write_cursor.lastrowid


def validate_api_key(db: 'DBHandler', key_hash: str) -> dict | None:
    """Validate an API key and return its details if valid
    
    Args:
        db: Database handler
        key_hash: Hashed API key to validate
    
    Returns:
        Dictionary with key details if valid, None if invalid or expired
    """
    from datetime import datetime
    
    with db.user_write() as write_cursor:
        # Get key details
        result = write_cursor.execute("""
            SELECT id, username, name, expires_at
            FROM api_keys
            WHERE key_hash = ?
        """, (key_hash,)).fetchone()
        
        if not result:
            return None
        
        key_id, username, name, expires_at = result
        
        # Check expiration
        if expires_at:
            expiry_dt = datetime.fromisoformat(expires_at)
            if expiry_dt < datetime.now():
                return None
        
        # Update last_used timestamp
        write_cursor.execute("""
            UPDATE api_keys
            SET last_used = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), key_id))
        
        return {
            'id': key_id,
            'username': username,
            'name': name,
        }


def revoke_api_key(db: 'DBHandler', key_id: int) -> bool:
    """Revoke an API key by ID
    
    Args:
        db: Database handler
        key_id: ID of the key to revoke
    
    Returns:
        True if key was revoked, False if not found
    """
    with db.user_write() as write_cursor:
        write_cursor.execute("""
            DELETE FROM api_keys
            WHERE id = ?
        """, (key_id,))
        return write_cursor.rowcount > 0


def list_user_api_keys(db: 'DBHandler', username: str) -> list[dict]:
    """List all API keys for a user
    
    Args:
        db: Database handler
        username: Username to list keys for
    
    Returns:
        List of dictionaries containing key information
    """
    with db.user_read() as read_cursor:
        results = read_cursor.execute("""
            SELECT id, name, created_at, last_used, expires_at
            FROM api_keys
            WHERE username = ?
            ORDER BY created_at DESC
        """, (username,)).fetchall()
        
        return [
            {
                'id': row[0],
                'name': row[1],
                'created_at': row[2],
                'last_used': row[3],
                'expires_at': row[4],
            }
            for row in results
        ]


if __name__ == '__main__':
    # This allows the script to be run standalone for testing
    import sys
    from rotkehlchen.db.dbhandler import DBHandler
    
    if len(sys.argv) != 2:
        print('Usage: python add_api_keys_table.py <data_directory>')
        sys.exit(1)
    
    data_dir = sys.argv[1]
    db = DBHandler(data_dir=data_dir)
    
    run_migration(db)
    print('Migration completed successfully')