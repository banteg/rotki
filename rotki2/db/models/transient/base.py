"""Base class for transient database models using SQLModel"""

from sqlalchemy import MetaData
from sqlmodel import SQLModel

metadata = MetaData()


class Base(SQLModel):
    """Base class for all transient database models"""
    __abstract__ = True
    metadata = metadata
