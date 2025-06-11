"""Additional SQLAlchemy models for user database tables"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CHAR,
    INTEGER,
    TEXT,
    VARCHAR,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rotkehlchen.db.orm.base import Base
from rotkehlchen.db.orm.types import BooleanType, FValType, TimestampType

if TYPE_CHECKING:
    from rotkehlchen.db.orm.enums import Location
    from rotkehlchen.db.orm.models import Asset, BlockchainAccount, Settings


class ExternalServiceCredentials(Base):
    """Model for external service credentials table"""
    __tablename__ = 'external_service_credentials'

    name: Mapped[str] = mapped_column(VARCHAR(30), primary_key=True, nullable=False)
    api_key: Mapped[str] = mapped_column(TEXT, nullable=False)
    api_secret: Mapped[str | None] = mapped_column(TEXT)

    def __repr__(self) -> str:
        return f"<ExternalServiceCredentials(name='{self.name}')>"


class Xpub(Base):
    """Model for xpubs table"""
    __tablename__ = 'xpubs'

    xpub: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    derivation_path: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    label: Mapped[str | None] = mapped_column(TEXT)
    blockchain: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)

    # Relationships
    mappings: Mapped[list['XpubMapping']] = relationship(
        back_populates='xpub_ref',
        cascade='all, delete-orphan',
    )

    def __repr__(self) -> str:
        return f"<Xpub(xpub='{self.xpub[:10]}...', blockchain='{self.blockchain}')>"


class XpubMapping(Base):
    """Model for xpub mappings table"""
    __tablename__ = 'xpub_mappings'

    address: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    xpub: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    derivation_path: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    account_index: Mapped[int | None] = mapped_column(INTEGER)
    derived_index: Mapped[int | None] = mapped_column(INTEGER)
    blockchain: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)

    # Relationships
    account: Mapped['BlockchainAccount'] = relationship(back_populates='xpub_mappings')
    xpub_ref: Mapped['Xpub'] = relationship(back_populates='mappings')

    __table_args__ = (
        ForeignKeyConstraint(
            ['blockchain', 'address'],
            ['blockchain_accounts.blockchain', 'blockchain_accounts.account'],
            ondelete='CASCADE',
        ),
        ForeignKeyConstraint(
            ['xpub', 'derivation_path', 'blockchain'],
            ['xpubs.xpub', 'xpubs.derivation_path', 'xpubs.blockchain'],
            ondelete='CASCADE',
        ),
    )

    def __repr__(self) -> str:
        return f"<XpubMapping(address='{self.address}', xpub='{self.xpub[:10]}...')>"


class EvmAccountDetails(Base):
    """Model for EVM account details table"""
    __tablename__ = 'evm_accounts_details'

    account: Mapped[str] = mapped_column(VARCHAR(42), primary_key=True, nullable=False)
    chain_id: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    key: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    value: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)

    def __repr__(self) -> str:
        return f"<EvmAccountDetails(account='{self.account}', chain_id={self.chain_id}, key='{self.key}')>"


class MarginPosition(Base):
    """Model for margin positions table"""
    __tablename__ = 'margin_positions'

    id: Mapped[str] = mapped_column(TEXT, primary_key=True)
    location: Mapped[str] = mapped_column(
        CHAR(1),
        ForeignKey('location.location'),
        nullable=False,
        default='A',
    )
    open_time: Mapped[int | None] = mapped_column(TimestampType)
    close_time: Mapped[int | None] = mapped_column(TimestampType)
    profit_loss: Mapped[str | None] = mapped_column(FValType)
    pl_currency: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
        nullable=False,
    )
    fee: Mapped[str | None] = mapped_column(FValType)
    fee_currency: Mapped[str | None] = mapped_column(
        TEXT,
        ForeignKey('assets.identifier', onupdate='CASCADE'),
    )
    link: Mapped[str | None] = mapped_column(TEXT)
    notes: Mapped[str | None] = mapped_column(TEXT)

    # Relationships
    location_ref: Mapped['Location'] = relationship()
    pl_currency_ref: Mapped['Asset'] = relationship(foreign_keys=[pl_currency])
    fee_currency_ref: Mapped[Optional['Asset']] = relationship(foreign_keys=[fee_currency])

    def __repr__(self) -> str:
        return f"<MarginPosition(id='{self.id}', location='{self.location}')>"


class UsedQueryRange(Base):
    """Model for used query ranges table"""
    __tablename__ = 'used_query_ranges'

    name: Mapped[str] = mapped_column(VARCHAR(24), primary_key=True, nullable=False)
    start_ts: Mapped[int | None] = mapped_column(TimestampType)
    end_ts: Mapped[int | None] = mapped_column(TimestampType)

    def __repr__(self) -> str:
        return f"<UsedQueryRange(name='{self.name}', start={self.start_ts}, end={self.end_ts})>"


class MultiSettings(Base):
    """Model for multisettings table"""
    __tablename__ = 'multisettings'

    name: Mapped[str] = mapped_column(VARCHAR(24), nullable=False)
    value: Mapped[str | None] = mapped_column(TEXT)

    __table_args__ = (
        UniqueConstraint('name', 'value'),
    )

    def __repr__(self) -> str:
        return f"<MultiSettings(name='{self.name}', value='{self.value}')>"


class IgnoredAction(Base):
    """Model for ignored actions table"""
    __tablename__ = 'ignored_actions'

    identifier: Mapped[str] = mapped_column(TEXT, primary_key=True)

    def __repr__(self) -> str:
        return f"<IgnoredAction(identifier='{self.identifier}')>"


class ENSMapping(Base):
    """Model for ENS mappings table"""
    __tablename__ = 'ens_mappings'

    address: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    ens_name: Mapped[str | None] = mapped_column(TEXT, unique=True)
    last_update: Mapped[int] = mapped_column(TimestampType, nullable=False)
    last_avatar_update: Mapped[int] = mapped_column(TimestampType, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<ENSMapping(address='{self.address}', ens_name='{self.ens_name}')>"


class AddressBook(Base):
    """Model for address book table"""
    __tablename__ = 'address_book'

    address: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    blockchain: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)

    def __repr__(self) -> str:
        return f"<AddressBook(address='{self.address}', name='{self.name}')>"


class RPCNode(Base):
    """Model for RPC nodes table"""
    __tablename__ = 'rpc_nodes'

    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    endpoint: Mapped[str] = mapped_column(TEXT, nullable=False)
    owned: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    active: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    weight: Mapped[str] = mapped_column(FValType, nullable=False)
    blockchain: Mapped[str] = mapped_column(TEXT, nullable=False)

    __table_args__ = (
        UniqueConstraint('endpoint', 'blockchain'),
        CheckConstraint('owned IN (0, 1)'),
        CheckConstraint('active IN (0, 1)'),
    )

    def __repr__(self) -> str:
        return f"<RPCNode(id={self.identifier}, name='{self.name}', blockchain='{self.blockchain}')>"


class UserNote(Base):
    """Model for user notes table"""
    __tablename__ = 'user_notes'

    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    title: Mapped[str] = mapped_column(TEXT, nullable=False)
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    location: Mapped[str] = mapped_column(TEXT, nullable=False)
    last_update_timestamp: Mapped[int] = mapped_column(TimestampType, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(BooleanType, nullable=False)

    __table_args__ = (
        CheckConstraint('is_pinned IN (0, 1)'),
    )

    def __repr__(self) -> str:
        return f"<UserNote(id={self.identifier}, title='{self.title}')>"


class AccountingRule(Base):
    """Model for accounting rules table"""
    __tablename__ = 'accounting_rules'

    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    type: Mapped[str] = mapped_column(TEXT, nullable=False)
    subtype: Mapped[str] = mapped_column(TEXT, nullable=False)
    counterparty: Mapped[str] = mapped_column(TEXT, nullable=False)
    taxable: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    count_entire_amount_spend: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    count_cost_basis_pnl: Mapped[bool] = mapped_column(BooleanType, nullable=False)
    accounting_treatment: Mapped[str | None] = mapped_column(TEXT)

    # Relationships
    linked_properties: Mapped[list['LinkedRuleProperty']] = relationship(
        back_populates='rule',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        UniqueConstraint('type', 'subtype', 'counterparty'),
        CheckConstraint('taxable IN (0, 1)'),
        CheckConstraint('count_entire_amount_spend IN (0, 1)'),
        CheckConstraint('count_cost_basis_pnl IN (0, 1)'),
    )

    def __repr__(self) -> str:
        return f"<AccountingRule(id={self.identifier}, type='{self.type}', subtype='{self.subtype}')>"


class LinkedRuleProperty(Base):
    """Model for linked rules properties table"""
    __tablename__ = 'linked_rules_properties'

    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    accounting_rule: Mapped[int | None] = mapped_column(
        INTEGER,
        ForeignKey('accounting_rules.identifier'),
    )
    property_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    setting_name: Mapped[str] = mapped_column(
        TEXT,
        ForeignKey('settings.name'),
        nullable=False,
    )

    # Relationships
    rule: Mapped[Optional['AccountingRule']] = relationship(back_populates='linked_properties')
    setting: Mapped['Settings'] = relationship()

    def __repr__(self) -> str:
        return f"<LinkedRuleProperty(id={self.identifier}, property='{self.property_name}')>"


class UnresolvedRemoteConflict(Base):
    """Model for unresolved remote conflicts table"""
    __tablename__ = 'unresolved_remote_conflicts'

    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    local_id: Mapped[int] = mapped_column(INTEGER, nullable=False)
    remote_data: Mapped[str] = mapped_column(TEXT, nullable=False)
    type: Mapped[int] = mapped_column(INTEGER, nullable=False)

    def __repr__(self) -> str:
        return f'<UnresolvedRemoteConflict(id={self.identifier}, type={self.type})>'


class KeyValueCache(Base):
    """Model for key value cache table"""
    __tablename__ = 'key_value_cache'

    name: Mapped[str] = mapped_column(TEXT, primary_key=True, nullable=False)
    value: Mapped[str | None] = mapped_column(TEXT)

    def __repr__(self) -> str:
        return f"<KeyValueCache(name='{self.name}')>"


class Calendar(Base):
    """Model for calendar table"""
    __tablename__ = 'calendar'

    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    timestamp: Mapped[int] = mapped_column(TimestampType, nullable=False)
    description: Mapped[str | None] = mapped_column(TEXT)
    counterparty: Mapped[str | None] = mapped_column(TEXT)
    address: Mapped[str | None] = mapped_column(TEXT)
    blockchain: Mapped[str | None] = mapped_column(TEXT)
    color: Mapped[str | None] = mapped_column(TEXT)
    auto_delete: Mapped[bool] = mapped_column(BooleanType, nullable=False)

    # Relationships
    reminders: Mapped[list['CalendarReminder']] = relationship(
        back_populates='event',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['blockchain', 'address'],
            ['blockchain_accounts.blockchain', 'blockchain_accounts.account'],
            ondelete='CASCADE',
        ),
        UniqueConstraint('name', 'address', 'blockchain'),
        CheckConstraint('auto_delete IN (0, 1)'),
    )

    def __repr__(self) -> str:
        return f"<Calendar(id={self.identifier}, name='{self.name}')>"


class CalendarReminder(Base):
    """Model for calendar reminders table"""
    __tablename__ = 'calendar_reminders'

    identifier: Mapped[int] = mapped_column(INTEGER, primary_key=True, nullable=False)
    event_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey('calendar.identifier', ondelete='CASCADE'),
        nullable=False,
    )
    secs_before: Mapped[int] = mapped_column(INTEGER, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(BooleanType, nullable=False, default=False)

    # Relationships
    event: Mapped['Calendar'] = relationship(back_populates='reminders')

    __table_args__ = (
        CheckConstraint('acknowledged IN (0, 1)'),
    )

    def __repr__(self) -> str:
        return f'<CalendarReminder(id={self.identifier}, event_id={self.event_id})>'


# Import to avoid circular dependency
