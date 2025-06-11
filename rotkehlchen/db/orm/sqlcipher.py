"""SQLCipher dialect configuration for SQLAlchemy"""

from sqlalchemy.dialects import registry
from sqlalchemy.dialects.sqlite import pysqlite
from sqlalchemy.pool import NullPool

# Register the pysqlcipher dialect if not already registered
try:
    registry.register('sqlite.pysqlcipher', 'sqlalchemy_sqlcipher.pysqlcipher', 'dialect')
except:
    # If sqlalchemy-sqlcipher is not available, create a basic dialect
    class SQLCipherDialect(pysqlite.SQLiteDialect_pysqlite):
        name = 'sqlite'
        driver = 'pysqlcipher'

        @classmethod
        def dbapi(cls):
            from pysqlcipher3 import dbapi2
            return dbapi2

        def on_connect(self):
            # Get the base on_connect behavior
            base_on_connect = super().on_connect()

            def connect(conn):
                # Call base behavior if exists
                if base_on_connect:
                    base_on_connect(conn)

                # SQLCipher specific configuration is handled in base.py
                # via event listeners

            return connect

        def get_pool_class(self, url):
            # Use NullPool to avoid connection pooling issues with encryption
            return NullPool

    # Register our custom dialect
    registry.register('sqlite.pysqlcipher', __name__, 'SQLCipherDialect')
