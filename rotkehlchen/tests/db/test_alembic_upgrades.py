"""Test Alembic migrations using the existing upgrade test logic

This module repurposes the old upgrade tests to work with Alembic migrations.
It runs the same checks but uses Alembic to perform the migrations.
"""

import os
import shutil
from contextlib import ExitStack, suppress
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pysqlcipher3 import dbapi2 as sqlcipher
from alembic import command
from alembic.config import Config

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_COW, A_ETH
from rotkehlchen.constants.misc import (
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    USERDB_NAME,
)
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.db.utils import table_exists
from rotkehlchen.db.alembic_manager import AlembicManager
from rotkehlchen.tests.utils.constants import A_LTC
from rotkehlchen.tests.utils.database import (
    _use_prepared_db,
    column_exists,
    mock_db_schema_sanity_check,
    mock_dbhandler_sync_globaldb_assets,
    mock_dbhandler_update_owned_assets,
)
from rotkehlchen.types import (
    ChainID,
    EvmTokenKind,
    Location,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


def target_patch(target_version: int):
    """Patch to make the upgrade manager think we want a specific version"""
    def new_get_version() -> int:
        return target_version
    return patch('rotkehlchen.db.settings.ROTKEHLCHEN_DB_VERSION', target_version)


def _init_db_with_alembic(
        user_data_dir: Path,
        msg_aggregator: MessagesAggregator,
        target_revision: str,
) -> DBHandler:
    """Initialize database and run Alembic migrations to target revision"""
    no_tables_created_after_init = patch(
        'rotkehlchen.db.dbhandler.DB_SCRIPT_CREATE_TABLES',
        new='',
    )
    
    with ExitStack() as stack:
        stack.enter_context(mock_db_schema_sanity_check())
        stack.enter_context(no_tables_created_after_init)
        stack.enter_context(mock_dbhandler_update_owned_assets())
        stack.enter_context(mock_dbhandler_sync_globaldb_assets())
        
        # Create initial DB connection
        db = DBHandler(
            user_data_dir=user_data_dir,
            password='123',
            msg_aggregator=msg_aggregator,
            initial_settings=None,
            sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
            resume_from_backup=False,
        )
        
        # Run Alembic migrations to specific revision
        alembic_cfg = Config(str(Path(__file__).parent.parent.parent / 'alembic.ini'))
        rotkehlchen_dir = Path(__file__).parent.parent.parent
        alembic_cfg.set_main_option('script_location', str(rotkehlchen_dir / 'db' / 'alembic'))
        
        # Set the database path in environment
        os.environ['ROTKEHLCHEN_DB_PATH'] = str(db.user_data_dir / 'rotkehlchen.db')
        os.environ['ROTKEHLCHEN_DB_PASSWORD'] = '123'
        
        # Run upgrade to specific revision
        command.upgrade(alembic_cfg, target_revision)
        
        return db


def get_alembic_revision_for_version(version: int) -> str:
    """Get the Alembic revision ID for a given database version"""
    if version == 26:
        return '001_initial_v26'
    elif version == 27:
        return '026_v26_to_v27'
    elif version == 28:
        return '027_v27_to_v28'
    elif version == 29:
        return '028_v28_to_v29'
    elif version == 30:
        return '029_v29_to_v30'
    elif version == 31:
        return '030_v30_to_v31'
    elif version == 32:
        return '031_v31_to_v32'
    elif version == 33:
        return '032_v32_to_v33'
    elif version == 34:
        return '033_v33_to_v34'
    elif version == 35:
        return '034_v34_to_v35'
    elif version == 36:
        return '035_v35_to_v36'
    elif version == 37:
        return '036_v36_to_v37'
    elif version == 38:
        return '037_v37_to_v38'
    elif version == 39:
        return '038_v38_to_v39'
    elif version == 40:
        return '039_v39_to_v40'
    elif version == 41:
        return '040_v40_to_v41'
    elif version == 42:
        return '041_v41_to_v42'
    elif version == 43:
        return '042_v42_to_v43'
    elif version == 44:
        return '043_v43_to_v44'
    elif version == 45:
        return '044_v44_to_v45'
    elif version == 46:
        return '045_v45_to_v46'
    elif version == 47:
        return '046_v46_to_v47'
    elif version == 48:
        return '047_v47_to_v48'
    else:
        raise ValueError(f"Unknown version: {version}")


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_alembic_upgrade_db_26_to_27(user_data_dir):
    """Test upgrading the DB from version 26 to version 27 using Alembic.
    
    - Recreates balancer events, uniswap events, amm_swaps. Deletes balancer pools
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v26_rotkehlchen.db')
    
    # Initialize at v26
    db_v26 = _init_db_with_alembic(
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        target_revision='001_initial_v26',
    )
    
    # Checks before migration
    cursor = db_v26.conn.cursor()
    assert cursor.execute(
        "SELECT COUNT(*) from used_query_ranges WHERE name LIKE 'uniswap%';",
    ).fetchone()[0] == 2
    assert cursor.execute(
        "SELECT COUNT(*) from used_query_ranges WHERE name LIKE 'balancer%';",
    ).fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges;').fetchone()[0] == 6
    assert cursor.execute('SELECT COUNT(*) from uniswap_events;').fetchone()[0] == 18
    assert cursor.execute('SELECT COUNT(*) from amm_swaps;').fetchone()[0] == 1
    assert cursor.execute('SELECT COUNT(*) from balancer_pools;').fetchone()[0] == 2
    assert cursor.execute('SELECT COUNT(*) from balancer_events;').fetchone()[0] == 15
    
    # Execute Alembic upgrade
    db_v26.logout()
    db = _init_db_with_alembic(
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        target_revision='026_v26_to_v27',
    )
    cursor = db.conn.cursor()
    
    # Check that upgrade worked
    assert cursor.execute(
        "SELECT COUNT(*) from used_query_ranges WHERE name LIKE 'uniswap%';",
    ).fetchone()[0] == 0
    assert cursor.execute(
        "SELECT COUNT(*) from used_query_ranges WHERE name LIKE 'balancer%';",
    ).fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from used_query_ranges;').fetchone()[0] == 4
    assert cursor.execute('SELECT COUNT(*) from uniswap_events;').fetchone()[0] == 0
    assert cursor.execute('SELECT COUNT(*) from amm_swaps;').fetchone()[0] == 0
    assert table_exists(cursor, 'balancer_pools') is False
    assert cursor.execute('SELECT COUNT(*) from balancer_events;').fetchone()[0] == 0
    db.logout()


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_alembic_upgrade_db_27_to_28(user_data_dir):
    """Test upgrading the DB from version 27 to version 28 using Alembic.
    
    - Deletes all kraken asset movements
    """
    msg_aggregator = MessagesAggregator()
    _use_prepared_db(user_data_dir, 'v27_rotkehlchen.db')
    
    # Initialize at v27  
    db_v27 = _init_db_with_alembic(
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        target_revision='026_v26_to_v27',
    )
    
    # Checks before migration
    cursor = db_v27.conn.cursor()
    assert cursor.execute('SELECT COUNT(*) from asset_movements WHERE location="C";').fetchone()[0] == 2  # noqa: E501
    
    # Execute Alembic upgrade
    db_v27.logout()
    db = _init_db_with_alembic(
        user_data_dir=user_data_dir,
        msg_aggregator=msg_aggregator,
        target_revision='027_v27_to_v28',
    )
    
    # Check results
    cursor = db.conn.cursor()
    assert cursor.execute('SELECT COUNT(*) from asset_movements WHERE location="C";').fetchone()[0] == 0  # noqa: E501
    db.logout()


# Add more test functions for other version upgrades following the same pattern...