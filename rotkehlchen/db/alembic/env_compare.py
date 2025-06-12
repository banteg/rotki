"""
Modified env.py for comparing schemas between two databases
Used by autogenerate_from_upgrades.py
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import create_engine, MetaData
from alembic import context

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# For comparison, we'll use reflection instead of models
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with comparison support."""
    
    # Get the target database URL from config
    target_url = config.get_main_option("sqlalchemy.url")
    
    # Check if we're doing a comparison
    compare_db = os.environ.get('ALEMBIC_COMPARE_DB')
    
    if compare_db:
        # We're comparing two databases
        # Create engines for both databases
        source_engine = create_engine(f'sqlite:///{compare_db}')
        target_engine = create_engine(target_url)
        
        # Reflect the source schema
        source_metadata = MetaData()
        source_metadata.reflect(bind=source_engine)
        
        # Reflect the target schema
        target_metadata = MetaData()
        target_metadata.reflect(bind=target_engine)
        
        # Use the target connection for the migration context
        with target_engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_metadata=source_metadata,  # Custom attribute for comparison
                render_as_batch=True,
                compare_type=True,
                include_schemas=True,
            )
            
            with context.begin_transaction():
                context.run_migrations()
    else:
        # Normal migration mode
        connectable = create_engine(target_url)
        
        with connectable.connect() as connection:
            # Reflect the current schema
            metadata = MetaData()
            metadata.reflect(bind=connection)
            
            context.configure(
                connection=connection,
                target_metadata=metadata,
                render_as_batch=True,
                compare_type=True,
            )
            
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()