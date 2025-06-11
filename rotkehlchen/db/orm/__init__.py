"""SQLAlchemy ORM models for rotkehlchen database

This module serves as a compatibility layer during migration to SQLModel.
It re-exports models from the new db.models package structure.
"""

# Import everything from the new model packages
from rotkehlchen.db.models.user import *  # noqa: F403
from rotkehlchen.db.models.global import *  # noqa: F403
from rotkehlchen.db.models.transient import *  # noqa: F403

# Re-export base classes with old names for compatibility
from rotkehlchen.db.models.user import Base as UserDBBase
from rotkehlchen.db.models.global import Base as GlobalDBBase
from rotkehlchen.db.models.transient import Base as TransientDBBase

# Create a generic Base for compatibility
Base = UserDBBase

# Additional exports that might be needed
__all__ = [
    # Base classes
    'Base',
    'UserDBBase', 
    'GlobalDBBase',
    'TransientDBBase',
    # All models are re-exported via star imports above
]