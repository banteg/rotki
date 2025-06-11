"""Settings and configuration models for global database using SQLModel"""

from typing import Optional

from sqlalchemy import TEXT, VARCHAR, Column
from sqlmodel import Field

from rotkehlchen.db.orm.types import BooleanType
from rotkehlchen.db.models.global.base import Base


class GlobalSettings(Base, table=True):
    """Model for global settings table"""
    __tablename__ = 'settings'

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    value: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<GlobalSettings(name='{self.name}', value='{self.value}')>"


class DefaultRPCNode(Base, table=True):
    """Model for default RPC nodes table"""
    __tablename__ = 'default_rpc_nodes'

    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    endpoint: str = Field(sa_column=Column(TEXT, nullable=False))
    owned: bool = Field(sa_column=Column(BooleanType, nullable=False))
    active: bool = Field(sa_column=Column(BooleanType, nullable=False))
    weight: str = Field(sa_column=Column(TEXT, nullable=False))
    blockchain: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))

    def __repr__(self) -> str:
        return f"<DefaultRPCNode(name='{self.name}', blockchain='{self.blockchain}')>"