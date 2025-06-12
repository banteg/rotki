import os
import sys
from logging.config import fileConfig
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import create_engine, engine_from_config, pool
from alembic import context
try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    HAS_SQLCIPHER = True
except ImportError:
    HAS_SQLCIPHER = False

# Only import what we need for user database migrations
from rotkehlchen.db.models.user.base import Base as UserBase

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all model modules to ensure they are registered
try:
    # Import all user models to ensure metadata is populated
    import rotkehlchen.db.models.user.accounts  # noqa: F401
    import rotkehlchen.db.models.user.accounting  # noqa: F401
    import rotkehlchen.db.models.user.address_book  # noqa: F401
    import rotkehlchen.db.models.user.cache  # noqa: F401
    import rotkehlchen.db.models.user.calendar  # noqa: F401
    import rotkehlchen.db.models.user.conflicts  # noqa: F401
    import rotkehlchen.db.models.user.defi  # noqa: F401
    import rotkehlchen.db.models.user.ens  # noqa: F401
    import rotkehlchen.db.models.user.evm  # noqa: F401
    import rotkehlchen.db.models.user.history  # noqa: F401
    import rotkehlchen.db.models.user.models  # noqa: F401
    import rotkehlchen.db.models.user.nfts  # noqa: F401
    import rotkehlchen.db.models.user.nodes  # noqa: F401
    import rotkehlchen.db.models.user.notes  # noqa: F401
    import rotkehlchen.db.models.user.services  # noqa: F401
    import rotkehlchen.db.models.user.staking  # noqa: F401
    import rotkehlchen.db.models.user.trading  # noqa: F401
    import rotkehlchen.db.models.user.xpubs  # noqa: F401
    import rotkehlchen.db.models.user.zksynclite  # noqa: F401
except ImportError:
    # Models may not be available in all contexts
    pass

# Use the UserBase metadata for migrations
target_metadata = UserBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """Get the database URL from environment or config."""
    # First check environment variable
    db_path = os.environ.get('ROTKEHLCHEN_DB_PATH')
    if db_path:
        return f'sqlite:///{db_path}'
    
    # Fall back to config
    url = config.get_main_option("sqlalchemy.url")
    if url and url != "driver://user:pass@localhost/dbname":
        return url
    
    # Default to a test database
    return 'sqlite:///rotkehlchen_test.db'


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite requires batch mode for some operations
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()
    
    # Check if we need to use sqlcipher
    db_path = os.environ.get('ROTKEHLCHEN_DB_PATH')
    password = os.environ.get('ROTKEHLCHEN_DB_PASSWORD')
    
    if db_path and password and HAS_SQLCIPHER:
        # Use pysqlcipher3 for encrypted databases
        # Create a custom connection creator that handles sqlcipher setup
        def creator():
            conn = sqlcipher.connect(db_path)
            conn.execute(f"PRAGMA key = '{password}'")
            return conn
        
        connectable = create_engine(
            'sqlite://',
            creator=creator,
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                compare_type=True,
                compare_server_default=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    else:
        # Use regular SQLite
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                compare_type=True,
                compare_server_default=True,
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
