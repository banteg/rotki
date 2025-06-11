"""Custom SQLAlchemy types for rotkehlchen database models"""

from typing import Any, Optional

from sqlalchemy import TypeDecorator, String, Integer
from sqlalchemy.engine.interfaces import Dialect


class FValType(TypeDecorator):
    """Type for FVal decimal values stored as strings"""
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return value


class TimestampType(TypeDecorator):
    """Type for timestamps stored as integers"""
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[int]:
        if value is None:
            return None
        return int(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return value


class BooleanType(TypeDecorator):
    """Type for booleans stored as integers (0/1) in SQLite"""
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[int]:
        if value is None:
            return None
        return 1 if value else 0

    def process_result_value(self, value: Any, dialect: Dialect) -> Optional[bool]:
        if value is None:
            return None
        return bool(value)