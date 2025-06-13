"""Authentication-related models for user database using SQLModel"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DATETIME, INTEGER, TEXT, VARCHAR, Column, ForeignKey
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.user.base import Base


class UserAccount(Base, table=True):
    """Model for user accounts table"""
    __tablename__ = 'user_accounts'

    username: str = Field(sa_column=Column(VARCHAR(255), primary_key=True, nullable=False))
    password_hash: str = Field(sa_column=Column(TEXT, nullable=False))
    created_at: datetime = Field(sa_column=Column(DATETIME, nullable=False))
    last_login: datetime | None = Field(default=None, sa_column=Column(DATETIME, nullable=True))

    # Relationships
    api_keys: list['ApiKey'] = Relationship(back_populates='user', cascade_delete=True)

    def __repr__(self) -> str:
        return f"<UserAccount(username='{self.username}')>"


class ApiKey(Base, table=True):
    """Model for API keys table"""
    __tablename__ = 'api_keys'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, autoincrement=True))
    username: str = Field(
        sa_column=Column(
            VARCHAR(255),
            ForeignKey('user_accounts.username', ondelete='CASCADE'),
            nullable=False,
        ),
    )
    key_hash: str = Field(sa_column=Column(TEXT, nullable=False, unique=True))
    name: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    created_at: datetime = Field(sa_column=Column(DATETIME, nullable=False))
    last_used: datetime | None = Field(default=None, sa_column=Column(DATETIME, nullable=True))
    expires_at: datetime | None = Field(default=None, sa_column=Column(DATETIME, nullable=True))

    # Relationships
    user: Optional['UserAccount'] = Relationship(back_populates='api_keys')

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, username='{self.username}', name='{self.name}')>"
