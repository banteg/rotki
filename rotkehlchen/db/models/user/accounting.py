"""Accounting-related models for user database using SQLModel"""

from typing import Optional

from sqlalchemy import (
    INTEGER,
    TEXT,
    CheckConstraint,
    Column,
    ForeignKey,
    UniqueConstraint,
)
from sqlmodel import Field, Relationship

from rotkehlchen.db.models.types import BooleanType
from rotkehlchen.db.models.user.base import Base


class AccountingRule(Base, table=True):
    """Model for accounting rules table"""
    __tablename__ = 'accounting_rules'
    __table_args__ = (
        UniqueConstraint('type', 'subtype', 'counterparty'),
        CheckConstraint('taxable IN (0, 1)'),
        CheckConstraint('count_entire_amount_spend IN (0, 1)'),
        CheckConstraint('count_cost_basis_pnl IN (0, 1)'),
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    type: str = Field(sa_column=Column(TEXT, nullable=False))
    subtype: str = Field(sa_column=Column(TEXT, nullable=False))
    counterparty: str = Field(sa_column=Column(TEXT, nullable=False))
    taxable: bool = Field(sa_column=Column(BooleanType, nullable=False))
    count_entire_amount_spend: bool = Field(sa_column=Column(BooleanType, nullable=False))
    count_cost_basis_pnl: bool = Field(sa_column=Column(BooleanType, nullable=False))
    accounting_treatment: str | None = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    properties: list['LinkedRuleProperty'] = Relationship(
        back_populates='rule',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<AccountingRule(id={self.identifier}, type='{self.type}', subtype='{self.subtype}')>"


class LinkedRuleProperty(Base, table=True):
    """Model for linked rule properties table"""
    __tablename__ = 'linked_rules_properties'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    accounting_rule: int | None = Field(
        default=None,
        sa_column=Column(
            INTEGER,
            ForeignKey('accounting_rules.identifier'),
            nullable=True,
        ),
    )
    property_name: str = Field(sa_column=Column(TEXT, nullable=False))
    setting_name: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('settings.name'),
            nullable=False,
        ),
    )

    # Relationships
    rule: Optional['AccountingRule'] = Relationship(back_populates='properties')

    def __repr__(self) -> str:
        return f"<LinkedRuleProperty(id={self.identifier}, rule={self.accounting_rule}, property='{self.property_name}')>"
