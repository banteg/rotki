"""Trading domain repositories"""

from .margin_repository import MarginPositionRepository
from .query_range_repository import QueryRangeRepository

__all__ = ['MarginPositionRepository', 'QueryRangeRepository']