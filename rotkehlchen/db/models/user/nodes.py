"""Node-related models for user database using SQLModel"""

from sqlalchemy import INTEGER, TEXT, UniqueConstraint, Column
from sqlmodel import Field

from rotkehlchen.db.orm.types import BooleanType, FValType
from rotkehlchen.db.orm.userdb.base import Base


class RPCNode(Base, table=True):
    """Model for RPC nodes table"""
    __tablename__ = 'rpc_nodes'
    __table_args__ = (
        UniqueConstraint('endpoint', 'blockchain'),
    )

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    name: str = Field(sa_column=Column(TEXT, nullable=False))
    endpoint: str = Field(sa_column=Column(TEXT, nullable=False))
    owned: bool = Field(sa_column=Column(BooleanType, nullable=False))
    active: bool = Field(sa_column=Column(BooleanType, nullable=False))
    weight: str = Field(sa_column=Column(FValType, nullable=False))
    blockchain: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<RPCNode(id={self.id}, name='{self.name}', endpoint='{self.endpoint}')>"