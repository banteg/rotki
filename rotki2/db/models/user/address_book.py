"""Address book models for user database using SQLModel"""


from sqlalchemy import TEXT, Column
from sqlmodel import Field

from rotki2.db.models.user.base import Base


class AddressBook(Base, table=True):
    """Model for address book table"""
    __tablename__ = 'address_book'

    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    blockchain: str | None = Field(
        default=None,
        sa_column=Column(TEXT, primary_key=True),
    )
    name: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<AddressBook(address='{self.address}', name='{self.name}')>"
