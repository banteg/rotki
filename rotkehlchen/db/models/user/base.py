"""Base class for user database models using SQLModel"""

from sqlalchemy import MetaData
from sqlmodel import SQLModel


metadata = MetaData()


class Base(SQLModel):
    """Base class for all user database models"""
    __abstract__ = True
    metadata = metadata