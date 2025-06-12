"""Simple test to verify Alembic migrations work correctly

This tests the Alembic migrations by comparing schemas before and after.
"""

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    HAS_SQLCIPHER = True
except ImportError:
    HAS_SQLCIPHER = False
    sqlcipher = None

from rotkehlchen.tests.utils.database import _use_prepared_db


def decrypt_database(encrypted_db_path: Path, decrypted_db_path: Path, password: str = "123") -> None:
    """Decrypt an encrypted database to a regular SQLite database"""
    if not HAS_SQLCIPHER:
        raise ImportError("pysqlcipher3 is required to decrypt test databases")
        
    # Open encrypted database
    encrypted_conn = sqlcipher.connect(str(encrypted_db_path))
    encrypted_conn.execute(f"PRAGMA key = '{password}'")
    
    # Export to regular SQLite database
    encrypted_conn.execute(f"ATTACH DATABASE '{decrypted_db_path}' AS plaintext KEY ''")
    encrypted_conn.execute("SELECT sqlcipher_export('plaintext')")
    encrypted_conn.execute("DETACH DATABASE plaintext")
    encrypted_conn.close()


def get_table_info(db_path: Path, table_name: str) -> list:
    """Get column information for a table"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    info = cursor.fetchall()
    conn.close()
    return info


def get_all_tables(db_path: Path) -> list:
    """Get all table names from database"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


@pytest.mark.skipif(not HAS_SQLCIPHER, reason="pysqlcipher3 not available")
def test_alembic_migration_v26_to_v27():
    """Test Alembic migration from v26 to v27 produces correct schema changes"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Copy and decrypt v26 database
        encrypted_v26 = Path(__file__).parent.parent.parent / "tests" / "data" / "v26_rotkehlchen.db"
        decrypted_v26 = temp_path / "v26_decrypted.db"
        decrypt_database(encrypted_v26, decrypted_v26)
        
        # Copy and decrypt v27 database (for comparison)
        encrypted_v27 = Path(__file__).parent.parent.parent / "tests" / "data" / "v27_rotkehlchen.db"
        decrypted_v27 = temp_path / "v27_expected.db"
        decrypt_database(encrypted_v27, decrypted_v27)
        
        # Create a working copy of v26
        test_db = temp_path / "test.db"
        shutil.copy(decrypted_v26, test_db)
        
        # Setup Alembic config
        alembic_cfg_path = Path(__file__).parent.parent.parent / 'alembic.ini'
        alembic_cfg = Config(str(alembic_cfg_path))
        rotkehlchen_dir = Path(__file__).parent.parent.parent
        alembic_cfg.set_main_option('script_location', str(rotkehlchen_dir / 'db' / 'alembic'))
        
        # Set environment for plain SQLite (no encryption)
        os.environ['ROTKEHLCHEN_DB_PATH'] = str(test_db)
        os.environ.pop('ROTKEHLCHEN_DB_PASSWORD', None)
        
        # First stamp the database at v26
        command.stamp(alembic_cfg, "001_initial_v26")
        
        # Run migration to v27
        command.upgrade(alembic_cfg, "026_v26_to_v27")
        
        # Compare schemas
        # Check that balancer_pools table was dropped
        v26_tables = get_all_tables(decrypted_v26)
        test_tables = get_all_tables(test_db)
        v27_tables = get_all_tables(decrypted_v27)
        
        assert 'balancer_pools' in v26_tables
        assert 'balancer_pools' not in test_tables
        assert 'balancer_pools' not in v27_tables
        
        # Check balancer_events table changes
        v26_balancer_cols = {col[1] for col in get_table_info(decrypted_v26, 'balancer_events')}
        test_balancer_cols = {col[1] for col in get_table_info(test_db, 'balancer_events')}
        v27_balancer_cols = {col[1] for col in get_table_info(decrypted_v27, 'balancer_events')}
        
        assert 'pool_address' in v26_balancer_cols
        assert 'pool_address' not in test_balancer_cols
        assert 'pool_address_token' in test_balancer_cols
        assert test_balancer_cols == v27_balancer_cols
        
        # Check amm_swaps table changes
        v26_amm_cols = {col[1] for col in get_table_info(decrypted_v26, 'amm_swaps')}
        test_amm_cols = {col[1] for col in get_table_info(test_db, 'amm_swaps')}
        v27_amm_cols = {col[1] for col in get_table_info(decrypted_v27, 'amm_swaps')}
        
        # Columns that should be removed
        removed_cols = {
            'token0_address', 'token1_address', 'token0_symbol', 'token1_symbol',
            'token0_name', 'token1_name', 'token0_decimals', 'token1_decimals',
            'is_token0_unknown', 'is_token1_unknown'
        }
        
        for col in removed_cols:
            assert col in v26_amm_cols
            assert col not in test_amm_cols
            
        # New columns that should be added
        assert 'token0_identifier' in test_amm_cols
        assert 'token1_identifier' in test_amm_cols
        
        assert test_amm_cols == v27_amm_cols
        
        print("✓ Alembic migration v26 -> v27 produces correct schema changes")


@pytest.mark.skipif(not HAS_SQLCIPHER, reason="pysqlcipher3 not available")  
def test_alembic_migration_v28_to_v29():
    """Test Alembic migration from v28 to v29 produces correct schema changes"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Copy and decrypt v28 database
        encrypted_v28 = Path(__file__).parent.parent.parent / "tests" / "data" / "v28_rotkehlchen.db"
        decrypted_v28 = temp_path / "v28_decrypted.db"
        decrypt_database(encrypted_v28, decrypted_v28)
        
        # Copy and decrypt v29 database (for comparison)
        encrypted_v29 = Path(__file__).parent.parent.parent / "tests" / "data" / "v29_rotkehlchen.db"
        decrypted_v29 = temp_path / "v29_expected.db"
        decrypt_database(encrypted_v29, decrypted_v29)
        
        # Create a working copy of v28
        test_db = temp_path / "test.db"
        shutil.copy(decrypted_v28, test_db)
        
        # Setup Alembic config
        alembic_cfg_path = Path(__file__).parent.parent.parent / 'alembic.ini'
        alembic_cfg = Config(str(alembic_cfg_path))
        rotkehlchen_dir = Path(__file__).parent.parent.parent
        alembic_cfg.set_main_option('script_location', str(rotkehlchen_dir / 'db' / 'alembic'))
        
        # Set environment for plain SQLite (no encryption)
        os.environ['ROTKEHLCHEN_DB_PATH'] = str(test_db)
        os.environ.pop('ROTKEHLCHEN_DB_PASSWORD', None)
        
        # First stamp the database at v28
        command.stamp(alembic_cfg, "027_v27_to_v28")
        
        # Run migration to v29
        command.upgrade(alembic_cfg, "028_v28_to_v29")
        
        # Get tables from both databases
        test_tables = get_all_tables(test_db)
        v29_tables = get_all_tables(decrypted_v29)
        
        # Check that new tables were created
        new_tables = {'xpubs', 'xpub_mappings'}
        for table in new_tables:
            assert table in test_tables
            assert table in v29_tables
            
        print("✓ Alembic migration v28 -> v29 produces correct schema changes")