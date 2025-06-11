"""Test database initialization and management"""


from rotkehlchen.db.orm.database import RotkehlchenDatabase, create_database


class TestDatabaseInitialization:
    """Test database initialization"""

    def test_create_new_database(self, tmp_path):
        """Test creating new database"""
        # Create global db directory
        global_dir = tmp_path / 'global'
        global_dir.mkdir()
        global_db = global_dir / 'global.db'

        # Create minimal global database
        import sqlite3
        conn = sqlite3.connect(str(global_db))
        conn.execute('CREATE TABLE info (version INTEGER)')
        conn.close()

        # Create user database
        user_dir = tmp_path / 'user'
        user_dir.mkdir()

        db = create_database(
            user_data_dir=user_dir,
            password='test123',
            echo_sql=False,
        )

        try:
            # Check database was created
            assert (user_dir / 'rotkehlchen.db').exists()

            # Check version was set
            version = db.get_version()
            assert version == 48  # USERDB_VERSION

            # Check repositories are available
            assert db.repos is not None
            assert db.global_repos is not None
            assert db.transient_repos is not None
        finally:
            db.close()

    def test_open_existing_database(self, orm_database):
        """Test opening existing database"""
        # Database is already created by fixture

        # Check we can read version
        version = orm_database.get_version()
        assert version == 48

        # Check we can use repositories
        orm_database.repos.settings.set_setting('test', 'value')
        value = orm_database.repos.settings.get_setting('test')
        assert value == 'value'

    def test_database_backup(self, orm_database, tmp_path):
        """Test database backup functionality"""
        # Add some data
        orm_database.repos.settings.set_setting('backup_test', 'backup_value')
        orm_database.repos.tags.add_tag('backup_tag', 'Tag', '000000', 'FFFFFF')
        orm_database.session_manager.user_session.commit()

        # Create backup
        backup_path = tmp_path / 'backup.db'
        result_path = orm_database.backup(backup_path)

        assert result_path == backup_path
        assert backup_path.exists()

        # Verify backup contains data
        import sqlite3
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()

        # Check settings
        cursor.execute('SELECT value FROM settings WHERE name = ?', ('backup_test',))
        value = cursor.fetchone()
        assert value[0] == 'backup_value'

        # Check tags
        cursor.execute('SELECT description FROM tags WHERE name = ?', ('backup_tag',))
        desc = cursor.fetchone()
        assert desc[0] == 'Tag'

        conn.close()

    def test_database_restore(self, tmp_path):
        """Test database restore functionality"""
        # Create directories
        user_dir = tmp_path / 'user'
        user_dir.mkdir()
        global_dir = tmp_path / 'global'
        global_dir.mkdir()
        global_db = global_dir / 'global.db'

        # Create minimal global database
        import sqlite3
        conn = sqlite3.connect(str(global_db))
        conn.execute('CREATE TABLE info (version INTEGER)')
        conn.close()

        # Create original database
        db1 = create_database(user_dir, password='test123')

        # Add data
        db1.repos.settings.set_setting('original', 'data')
        db1.session_manager.user_session.commit()

        # Create backup
        backup_path = tmp_path / 'backup.db'
        db1.backup(backup_path)

        # Modify original
        db1.repos.settings.set_setting('original', 'modified')
        db1.session_manager.user_session.commit()

        # Close original
        db1.close()

        # Create new database instance
        db2 = create_database(user_dir, password='test123')

        # Verify modified data
        assert db2.repos.settings.get_setting('original') == 'modified'

        # Restore from backup
        db2.restore(backup_path)

        # Verify restored data
        assert db2.repos.settings.get_setting('original') == 'data'

        db2.close()

    def test_context_manager(self, tmp_path):
        """Test database as context manager"""
        # Setup
        user_dir = tmp_path / 'user'
        user_dir.mkdir()
        global_dir = tmp_path / 'global'
        global_dir.mkdir()
        global_db = global_dir / 'global.db'

        import sqlite3
        conn = sqlite3.connect(str(global_db))
        conn.execute('CREATE TABLE info (version INTEGER)')
        conn.close()

        # Use as context manager
        with RotkehlchenDatabase(user_dir, password='test123') as db:
            db.repos.settings.set_setting('context_test', 'value')
            db.session_manager.user_session.commit()

        # Verify database was closed properly
        # Open again to check data persisted
        with RotkehlchenDatabase(user_dir, password='test123') as db:
            value = db.repos.settings.get_setting('context_test')
            assert value == 'value'


class TestRepositoryManager:
    """Test repository manager functionality"""

    def test_repository_manager_initialization(self, orm_database):
        """Test all repositories are initialized"""
        repos = orm_database.repos

        # Check account repositories
        assert repos.accounts is not None
        assert repos.tags is not None
        assert repos.xpubs is not None
        assert repos.evm_account_details is not None
        assert repos.credentials is not None

        # Check asset repositories
        assert repos.assets is not None
        assert repos.owned_assets is not None

        # Check balance repositories
        assert repos.manual_balances is not None
        assert repos.timed_balances is not None

        # Check all other repositories
        assert repos.margin_positions is not None
        assert repos.query_ranges is not None
        assert repos.history_events is not None
        assert repos.evm_transactions is not None
        assert repos.settings is not None
        assert repos.cache is not None
        assert repos.user_notes is not None
        assert repos.rpc_nodes is not None
        assert repos.eth2_validators is not None
        assert repos.eth2_staking is not None
        assert repos.cowswap is not None
        assert repos.gnosis_pay is not None
        assert repos.nfts is not None
        assert repos.premium is not None
        assert repos.location_data is not None
        assert repos.database_info is not None

    def test_global_repository_manager(self, orm_database):
        """Test global database repository manager"""
        global_repos = orm_database.global_repos

        # Check only global repositories are available
        assert global_repos.asset_collections is not None
        assert global_repos.asset_mappings is not None
        assert global_repos.asset_updates is not None
        assert global_repos.price_history is not None

        # Check user repositories are not available
        assert not hasattr(global_repos, 'accounts')
        assert not hasattr(global_repos, 'settings')

    def test_transient_repository_manager(self, orm_database):
        """Test transient database repository manager"""
        transient_repos = orm_database.transient_repos

        # Check only transient repositories are available
        assert transient_repos.abi_cache is not None
        assert transient_repos.address_book is not None
        assert transient_repos.calendar is not None

        # Check other repositories are not available
        assert not hasattr(transient_repos, 'accounts')
        assert not hasattr(transient_repos, 'price_history')
