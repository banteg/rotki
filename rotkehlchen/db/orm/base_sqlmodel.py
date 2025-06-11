"""SQLModel base classes for rotkehlchen database models"""

from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

# Create separate metadata instances for each database
# This is crucial to prevent table name collisions between databases
user_db_metadata = MetaData()
global_db_metadata = MetaData()
transient_db_metadata = MetaData()

# Create base classes with separate metadata
class UserDBBase(SQLModel):
    """Base class for User database models"""
    __abstract__ = True
    metadata = user_db_metadata

class GlobalDBBase(SQLModel):
    """Base class for Global database models"""
    __abstract__ = True
    metadata = global_db_metadata

class TransientDBBase(SQLModel):
    """Base class for Transient database models"""
    __abstract__ = True
    metadata = transient_db_metadata

# For compatibility with existing GeventSafeDatabase
class GeventSafeDatabase:
    """Compatibility wrapper for gevent-safe database operations"""
    
    def __init__(self, engine):
        self.engine = engine
        
    def get_session(self) -> Session:
        """Get a new session"""
        return Session(self.engine)