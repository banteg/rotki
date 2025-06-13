"""Node-related models for user database using SQLModel"""

from sqlalchemy import INTEGER, TEXT, CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field

from rotkehlchen.db.models.types import BooleanType
from rotkehlchen.db.models.user.base import Base


class RPCNode(Base, table=True):
    """Model for RPC nodes table"""
    __tablename__ = 'rpc_nodes'
    __table_args__ = (
        UniqueConstraint('endpoint', 'blockchain'),
        CheckConstraint('owned IN (0, 1)'),
        CheckConstraint('active IN (0, 1)'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    name: str = Field(sa_column=Column(TEXT, nullable=False))
    endpoint: str = Field(sa_column=Column(TEXT, nullable=False))
    owned: bool = Field(sa_column=Column(BooleanType, nullable=False))
    active: bool = Field(sa_column=Column(BooleanType, nullable=False))
    weight: str = Field(sa_column=Column(TEXT, nullable=False))
    blockchain: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<RPCNode(id={self.identifier}, name='{self.name}', endpoint='{self.endpoint}')>"
