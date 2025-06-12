"""Settings models for transient database using SQLModel"""


from sqlalchemy import TEXT, VARCHAR, Column
from sqlmodel import Field

from rotkehlchen.db.models.transient.base import Base


class TransientSettings(Base, table=True):
    """Model for transient settings table"""
    __tablename__ = 'settings'

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    value: str | None = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<TransientSettings(name='{self.name}', value='{self.value}')>"
