"""Settings and configuration models for global database using SQLModel"""


from sqlalchemy import INTEGER, TEXT, VARCHAR, Column
from sqlmodel import Field

from rotki2.db.models.globaldb.base import Base


class GlobalSettings(Base, table=True):
    """Model for global settings table"""
    __tablename__ = 'settings'

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    value: str | None = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<GlobalSettings(name='{self.name}', value='{self.value}')>"


class DefaultRPCNode(Base, table=True):
    """Model for default RPC nodes table"""
    __tablename__ = 'default_rpc_nodes'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    name: str = Field(sa_column=Column(TEXT, nullable=False))
    endpoint: str = Field(sa_column=Column(TEXT, nullable=False))
    owned: int = Field(sa_column=Column(INTEGER, nullable=False))
    active: int = Field(sa_column=Column(INTEGER, nullable=False))
    weight: str = Field(sa_column=Column(TEXT, nullable=False))
    blockchain: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<DefaultRPCNode(id={self.identifier}, name='{self.name}', blockchain='{self.blockchain}')>"
