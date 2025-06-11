"""Contract-related models for global database using SQLModel"""

from typing import Optional

from sqlalchemy import INTEGER, TEXT, Column
from sqlmodel import Field

from rotkehlchen.db.models.global.base import Base


class ContractData(Base, table=True):
    """Model for contract data table"""
    __tablename__ = 'contract_data'

    chain_id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    abi: str = Field(sa_column=Column(TEXT, nullable=False))
    deployed_block: Optional[int] = Field(default=None, sa_column=Column(INTEGER))

    def __repr__(self) -> str:
        return f"<ContractData(chain_id={self.chain_id}, address='{self.address}')>"


class ContractABI(Base, table=True):
    """Model for contract ABI table"""
    __tablename__ = 'contract_abi'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    name: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<ContractABI(id={self.id}, name='{self.name}')>"