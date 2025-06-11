"""SQLModel models for additional user database tables"""

from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    CHAR, INTEGER, TEXT, VARCHAR, CheckConstraint, Column, ForeignKey,
    UniqueConstraint, Index, Computed
)
from sqlmodel import Field, Relationship

from rotkehlchen.db.orm.base_sqlmodel import UserDBBase
from rotkehlchen.db.orm.types import BooleanType, FValType, TimestampType

if TYPE_CHECKING:
    from rotkehlchen.db.orm.models_sqlmodel import BlockchainAccount, Location


class ExternalServiceCredentials(UserDBBase, table=True):
    """Model for external service credentials table"""
    __tablename__ = 'external_service_credentials'

    name: str = Field(sa_column=Column(VARCHAR(30), primary_key=True, nullable=False))
    api_key: str = Field(sa_column=Column(TEXT, nullable=False))
    api_secret: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    def __repr__(self) -> str:
        return f"<ExternalServiceCredentials(name='{self.name}')>"


class MarginPosition(UserDBBase, table=True):
    """Model for margin positions table"""
    __tablename__ = 'margin_positions'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        )
    )
    open_time: int = Field(sa_column=Column(TimestampType, nullable=False))
    close_time: int = Field(sa_column=Column(TimestampType, nullable=False))
    profit_loss: str = Field(sa_column=Column(FValType, nullable=False))
    pl_currency: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    fee: str = Field(sa_column=Column(FValType, nullable=False))
    fee_currency: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    link: str = Field(sa_column=Column(TEXT, nullable=False))
    notes: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Relationships would go here

    def __repr__(self) -> str:
        return f"<MarginPosition(id={self.id}, location='{self.location}')>"


class RPCNode(UserDBBase, table=True):
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


class Xpub(UserDBBase, table=True):
    """Model for xpubs table"""
    __tablename__ = 'xpubs'

    xpub: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    derivation_path: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    label: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    mappings: List['XpubMapping'] = Relationship(
        back_populates='xpub_obj',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Xpub(xpub='{self.xpub}', label='{self.label}')>"


class XpubMapping(UserDBBase, table=True):
    """Model for xpub mappings table"""
    __tablename__ = 'xpub_mappings'

    xpub: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('xpubs.xpub', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )
    derivation_path: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    account_index: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    derived_index: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    blockchain: str = Field(
        sa_column=Column(
            VARCHAR(24),
            ForeignKey('blockchain_accounts.blockchain'),
            nullable=False,
        )
    )

    # Relationships
    xpub_obj: Optional['Xpub'] = Relationship(back_populates='mappings')
    account: Optional['BlockchainAccount'] = Relationship()

    def __repr__(self) -> str:
        return f"<XpubMapping(xpub='{self.xpub}', address='{self.address}')>"


class EvmAccountDetails(UserDBBase, table=True):
    """Model for EVM account details table"""
    __tablename__ = 'evm_accounts_details'

    account: str = Field(
        sa_column=Column(
            VARCHAR(42),
            ForeignKey('blockchain_accounts.account'),
            primary_key=True,
            nullable=False,
        )
    )
    chain_id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    last_queried_timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))

    # Relationships
    account_obj: Optional['BlockchainAccount'] = Relationship()

    def __repr__(self) -> str:
        return f"<EvmAccountDetails(account='{self.account}', chain_id={self.chain_id})>"


class UsedQueryRange(UserDBBase, table=True):
    """Model for used query ranges table"""
    __tablename__ = 'used_query_ranges'

    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    start_ts: Optional[int] = Field(default=None, sa_column=Column(TimestampType))
    end_ts: Optional[int] = Field(default=None, sa_column=Column(TimestampType))

    def __repr__(self) -> str:
        return f"<UsedQueryRange(name='{self.name}', start={self.start_ts}, end={self.end_ts})>"


class MultiSettings(UserDBBase, table=True):
    """Model for multisettings table"""
    __tablename__ = 'multisettings'
    __table_args__ = (
        UniqueConstraint('name', 'value'),
    )

    # SQLAlchemy requires a primary key, but the SQL doesn't define one
    # Using composite primary key as the closest match to UNIQUE(name, value)
    name: str = Field(sa_column=Column(VARCHAR(24), primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False, server_default=''))

    def __repr__(self) -> str:
        return f"<MultiSettings(name='{self.name}', value='{self.value}')>"


class KeyValueCache(UserDBBase, table=True):
    """Model for key value cache table"""
    __tablename__ = 'key_value_cache'

    name: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    value: str = Field(sa_column=Column(TEXT, nullable=False))
    last_queried_ts: int = Field(sa_column=Column(TimestampType, nullable=False))

    def __repr__(self) -> str:
        return f"<KeyValueCache(name='{self.name}')>"


class UserNote(UserDBBase, table=True):
    """Model for user notes table"""
    __tablename__ = 'user_notes'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    title: str = Field(sa_column=Column(TEXT, nullable=False))
    content: str = Field(sa_column=Column(TEXT, nullable=False))
    location: str = Field(
        sa_column=Column(
            CHAR(1),
            ForeignKey('location.location'),
            nullable=False,
            server_default='A',
        )
    )
    last_update_timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    is_pinned: bool = Field(sa_column=Column(BooleanType, nullable=False))

    # Relationships
    location_ref: Optional['Location'] = Relationship()

    def __repr__(self) -> str:
        return f"<UserNote(id={self.identifier}, title='{self.title}')>"


class ENSMapping(UserDBBase, table=True):
    """Model for ENS mappings table"""
    __tablename__ = 'ens_mappings'

    address: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    ens_name: Optional[str] = Field(default=None, sa_column=Column(TEXT, unique=True))
    last_update: int = Field(sa_column=Column(TimestampType, nullable=False))
    last_avatar_update: int = Field(sa_column=Column(TimestampType, nullable=False, server_default='0'))

    def __repr__(self) -> str:
        return f"<ENSMapping(address='{self.address}', ens_name='{self.ens_name}')>"


class CowswapOrder(UserDBBase, table=True):
    """Model for CoWSwap orders table"""
    __tablename__ = 'cowswap_orders'

    identifier: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    order_type: str = Field(sa_column=Column(TEXT, nullable=False))
    raw_fee_amount: str = Field(sa_column=Column(FValType, nullable=False))
    sell_token: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    buy_token: str = Field(
        sa_column=Column(
            TEXT,
            ForeignKey('assets.identifier', onupdate='CASCADE'),
            nullable=False,
        )
    )
    sell_amount: str = Field(sa_column=Column(FValType, nullable=False))
    buy_amount: str = Field(sa_column=Column(FValType, nullable=False))
    limit_price: Optional[str] = Field(default=None, sa_column=Column(FValType))
    fee_amount: str = Field(sa_column=Column(FValType, nullable=False))
    settlement_contract_address: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<CowswapOrder(identifier='{self.identifier}')>"


class GnosisPayData(UserDBBase, table=True):
    """Model for Gnosis Pay data table"""
    __tablename__ = 'gnosispay_data'

    tx_hash: str = Field(sa_column=Column(TEXT, primary_key=True, nullable=False))
    timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    merchant_name: str = Field(sa_column=Column(TEXT, nullable=False))
    merchant_city: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    country: str = Field(sa_column=Column(TEXT, nullable=False))
    mcc: int = Field(sa_column=Column(INTEGER, nullable=False))
    amount_in_eur: str = Field(sa_column=Column(FValType, nullable=False))

    def __repr__(self) -> str:
        return f"<GnosisPayData(tx_hash='{self.tx_hash}', merchant='{self.merchant_name}')>"


class AccountingRule(UserDBBase, table=True):
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
    accounting_treatment: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    properties: List['LinkedRuleProperty'] = Relationship(
        back_populates='rule',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<AccountingRule(id={self.id}, type='{self.type}', asset='{self.asset}')>"


class LinkedRuleProperty(UserDBBase, table=True):
    """Model for linked rule properties table"""
    __tablename__ = 'linked_rules_properties'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    rule_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('accounting_rules.identifier', ondelete='CASCADE'),
            nullable=False,
        )
    )
    property_name: str = Field(sa_column=Column(TEXT, nullable=False))
    setting_name: str = Field(sa_column=Column(TEXT, nullable=False))
    setting_value: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Relationships
    rule: Optional['AccountingRule'] = Relationship(back_populates='properties')

    def __repr__(self) -> str:
        return f"<LinkedRuleProperty(id={self.id}, rule_id={self.rule_id}, property='{self.property_name}')>"


class UnresolvedRemoteConflict(UserDBBase, table=True):
    """Model for unresolved remote conflicts table"""
    __tablename__ = 'unresolved_remote_conflicts'

    id: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    local_id: str = Field(sa_column=Column(TEXT, nullable=False))
    remote_id: str = Field(sa_column=Column(TEXT, nullable=False))
    type: str = Field(sa_column=Column(TEXT, nullable=False))
    local_data: str = Field(sa_column=Column(TEXT, nullable=False))
    remote_data: str = Field(sa_column=Column(TEXT, nullable=False))

    def __repr__(self) -> str:
        return f"<UnresolvedRemoteConflict(id={self.id}, type='{self.type}')>"


class Calendar(UserDBBase, table=True):
    """Model for calendar table"""
    __tablename__ = 'calendar'
    __table_args__ = (
        UniqueConstraint('name', 'address', 'blockchain'),
        # Note: The foreign key on (blockchain, address) references blockchain_accounts
        # but can be NULL, which is handled by the optional fields
    )

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    name: str = Field(sa_column=Column(TEXT, nullable=False))
    timestamp: int = Field(sa_column=Column(TimestampType, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    counterparty: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    address: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    blockchain: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    color: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    auto_delete: bool = Field(sa_column=Column(BooleanType, nullable=False))

    # Relationships
    reminders: List['CalendarReminder'] = Relationship(
        back_populates='calendar_entry',
        cascade_delete=True,
    )

    def __repr__(self) -> str:
        return f"<Calendar(id={self.identifier}, name='{self.name}')>"


class CalendarReminder(UserDBBase, table=True):
    """Model for calendar reminders table"""
    __tablename__ = 'calendar_reminders'

    identifier: int = Field(sa_column=Column(INTEGER, primary_key=True, nullable=False))
    event_id: int = Field(
        sa_column=Column(
            INTEGER,
            ForeignKey('calendar.identifier', ondelete='CASCADE'),
            nullable=False,
        )
    )
    secs_before: int = Field(sa_column=Column(INTEGER, nullable=False))
    acknowledged: bool = Field(sa_column=Column(BooleanType, nullable=False, server_default='0'))

    # Relationships
    calendar_entry: Optional['Calendar'] = Relationship(back_populates='reminders')

    def __repr__(self) -> str:
        return f"<CalendarReminder(id={self.id}, event_id={self.event_id})>"