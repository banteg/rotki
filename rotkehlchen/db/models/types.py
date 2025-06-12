"""Custom SQLAlchemy types for rotkehlchen database models"""

from typing import Any

from sqlalchemy import Integer, String, TypeDecorator
from sqlalchemy.engine.interfaces import Dialect


class FValType(TypeDecorator):
    """Type for FVal decimal values stored as strings"""
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return value


class TimestampType(TypeDecorator):
    """Type for timestamps stored as integers"""
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> int | None:
        if value is None:
            return None
        return int(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return value


class BooleanType(TypeDecorator):
    """Type for booleans stored as integers (0/1) in SQLite"""
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> int | None:
        if value is None:
            return None
        return 1 if value else 0

    def process_result_value(self, value: Any, dialect: Dialect) -> bool | None:
        if value is None:
            return None
        return bool(value)
