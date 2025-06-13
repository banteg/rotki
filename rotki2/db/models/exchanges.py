"""SQLModel models for exchange-related data"""
from typing import Any

from sqlalchemy import JSON, Column, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from rotkehlchen.types import Location


class ExchangeCredentials(SQLModel, table=True):
    """Exchange credentials storage"""
    
    __tablename__ = 'exchange_credentials'
    __table_args__ = (
        UniqueConstraint('name', 'location', name='unique_exchange_name_location'),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    location: str = Field(index=True)  # Location enum value
    api_key: str
    api_secret: str | None = None
    passphrase: str | None = None  # For exchanges like KuCoin, OKX
    
    def to_location_enum(self) -> Location:
        """Convert location string to Location enum"""
        return Location(self.location)


class ExchangeExtras(SQLModel, table=True):
    """Exchange-specific extra configuration"""
    
    __tablename__ = 'exchange_extras'
    __table_args__ = (
        UniqueConstraint('exchange_name', 'exchange_location', name='unique_exchange_extras'),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    exchange_name: str = Field(index=True)
    exchange_location: str = Field(index=True)
    extras: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Examples of extras:
    # Kraken: {'account_type': 'starter'|'intermediate'|'pro'}
    # Binance: {'selected_markets': ['BTCUSDT', 'ETHUSDT']}


class ExchangeCachedData(SQLModel, table=True):
    """Cached data from exchanges"""
    
    __tablename__ = 'exchange_cached_data'
    
    id: int | None = Field(default=None, primary_key=True)
    exchange_name: str = Field(index=True)
    exchange_location: str = Field(index=True)
    data_type: str = Field(index=True)  # 'balances', 'trades', 'deposits', 'withdrawals'
    timestamp: int  # When the data was cached
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class ExchangeTradePairs(SQLModel, table=True):
    """Available trading pairs for exchanges"""
    
    __tablename__ = 'exchange_trade_pairs'
    __table_args__ = (
        UniqueConstraint('exchange_location', 'pair', name='unique_location_pair'),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    exchange_location: str = Field(index=True)
    pair: str  # e.g., 'BTCUSDT'
    base_asset: str  # e.g., 'BTC'
    quote_asset: str  # e.g., 'USDT'
    active: bool = True
    min_trade_size: str | None = None
    timestamp: int  # When this data was last updated


class UserExchangePairs(SQLModel, table=True):
    """User-selected trading pairs for exchanges like Binance"""
    
    __tablename__ = 'user_exchange_pairs'
    __table_args__ = (
        UniqueConstraint('exchange_name', 'exchange_location', 'pair', name='unique_user_pair'),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    exchange_name: str = Field(index=True)
    exchange_location: str = Field(index=True)
    pair: str  # Trading pair like 'BTCUSDT'
    enabled: bool = True