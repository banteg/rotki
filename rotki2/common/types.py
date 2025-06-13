"""Common types for rotki2"""
from dataclasses import dataclass
from typing import Any, Literal, NewType

# Basic types
Timestamp = NewType('Timestamp', int)
Price = NewType('Price', float)
ApiKey = NewType('ApiKey', str)
ApiSecret = NewType('ApiSecret', str)


@dataclass
class PremiumCredentials:
    """Premium service credentials"""
    api_key: str
    api_secret: str


@dataclass
class ModifiableDBSettings:
    """Settings that can be modified by users"""
    main_currency: str | None = None
    ui_floating_precision: int | None = None
    active_modules: list[str] | None = None
    ignored_assets: list[str] | None = None
    btc_derivation_gap_limit: int | None = None
    ksm_rpc_endpoint: str | None = None
    dot_rpc_endpoint: str | None = None
    beacon_rpc_endpoint: str | None = None
    current_price_oracles: list[str] | None = None
    historical_price_oracles: list[str] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in self.__dict__.items() if v is not None}