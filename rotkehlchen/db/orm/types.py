"""Custom SQLAlchemy types for rotkehlchen database"""

from typing import TypeVar

from eth_typing import HexStr
from sqlalchemy import BLOB, CHAR, INTEGER, TEXT, TypeDecorator
from sqlalchemy.engine import Dialect

from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp

T = TypeVar('T')


class CharEnumType(TypeDecorator):
    """Type for CHAR(1) enum columns that map to string values"""
    impl = CHAR(1)
    cache_ok = True

    def __init__(self, enum_class: type[T], *args, **kwargs):
        self.enum_class = enum_class
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: T | None, dialect: Dialect) -> str | None:
        """Convert enum to database CHAR(1) value"""
        if value is None:
            return None
        # Assume enum has a method to get DB char value
        return getattr(value, 'serialize_for_db', lambda: str(value))()

    def process_result_value(self, value: str | None, dialect: Dialect) -> T | None:
        """Convert database CHAR(1) value to enum"""
        if value is None:
            return None
        # Assume enum has a method to deserialize from DB
        return getattr(self.enum_class, 'deserialize_from_db', self.enum_class)(value)


class HexBytesType(TypeDecorator):
    """Type for storing hex strings as BLOB in database"""
    impl = BLOB
    cache_ok = True

    def process_bind_param(self, value: HexStr | None, dialect: Dialect) -> bytes | None:
        """Convert hex string to bytes for storage"""
        if value is None:
            return None
        # Remove '0x' prefix if present
        hex_value = value.removeprefix('0x')
        return bytes.fromhex(hex_value)

    def process_result_value(self, value: bytes | None, dialect: Dialect) -> HexStr | None:
        """Convert bytes to hex string"""
        if value is None:
            return None
        return HexStr('0x' + value.hex())


class FValType(TypeDecorator):
    """Type for storing FVal (decimal) values as TEXT"""
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value: FVal | None, dialect: Dialect) -> str | None:
        """Convert FVal to string for storage"""
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> FVal | None:
        """Convert string to FVal"""
        if value is None:
            return None
        return FVal(value)


class TimestampType(TypeDecorator):
    """Type for storing timestamps as INTEGER"""
    impl = INTEGER
    cache_ok = True

    def process_bind_param(self, value: Timestamp | None, dialect: Dialect) -> int | None:
        """Convert Timestamp to int for storage"""
        if value is None:
            return None
        return int(value)

    def process_result_value(self, value: int | None, dialect: Dialect) -> Timestamp | None:
        """Convert int to Timestamp"""
        if value is None:
            return None
        return Timestamp(value)


class BooleanType(TypeDecorator):
    """Type for storing boolean as INTEGER (0/1) with CHECK constraint"""
    impl = INTEGER
    cache_ok = True

    def process_bind_param(self, value: bool | None, dialect: Dialect) -> int | None:
        """Convert boolean to int for storage"""
        if value is None:
            return None
        return 1 if value else 0

    def process_result_value(self, value: int | None, dialect: Dialect) -> bool | None:
        """Convert int to boolean"""
        if value is None:
            return None
        return bool(value)
