"""Contract-related models for global database using SQLModel"""


from sqlalchemy import INTEGER, TEXT, VARCHAR, Column, ForeignKey, UniqueConstraint
from sqlmodel import Field

from rotki2.db.models.globaldb.base import Base


class ContractData(Base, table=True):
    """Model for contract data table"""
    __tablename__ = 'contract_data'

    address: str = Field(sa_column=Column(VARCHAR(42), primary_key=True, nullable=False))
    chain_id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    abi: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('contract_abi.id', onupdate='CASCADE', ondelete='SET NULL'),
            nullable=False,
        ),
    )
    deployed_block: int | None = Field(default=None, sa_column=Column(INTEGER))

    def __repr__(self) -> str:
        return f"<ContractData(chain_id={self.chain_id}, address='{self.address}')>"


class ContractABI(Base, table=True):
    """Model for contract ABI table"""
    __tablename__ = 'contract_abi'
    __table_args__ = (
        UniqueConstraint('value'),
    )

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    name: str | None = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<ContractABI(id={self.id}, name='{self.name}')>"
