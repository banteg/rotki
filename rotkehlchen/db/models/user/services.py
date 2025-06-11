"""External service-related models for user database using SQLModel"""

from typing import Optional

from sqlalchemy import INTEGER, TEXT, VARCHAR, Column
from sqlmodel import Field

from rotkehlchen.db.orm.userdb.base import Base


class ExternalServiceCredentials(Base, table=True):
    """Model for external service credentials table"""
    __tablename__ = 'external_service_credentials'

    name: str = Field(sa_column=Column(VARCHAR(30), primary_key=True, nullable=False))
    api_key: str = Field(sa_column=Column(TEXT, nullable=False))
    api_secret: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<ExternalServiceCredentials(name='{self.name}')>"