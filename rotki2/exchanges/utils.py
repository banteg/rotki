"""Common utilities for exchange implementations"""
import hashlib
import hmac
import time
from typing import Any, Callable, TypeVar
from urllib.parse import urlencode

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade, TradeType
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp,
)
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now

logger = RotkehlchenLogsAdapter(__name__)

T = TypeVar('T')


def get_key_if_has_val(
    data: dict[str, Any],
    key: str,
    default: T | None = None,
) -> T | None:
    """Get a key from a dict but only if its value evaluates to True"""
    val = data.get(key, default)
    if val:
        return val
    return default


def create_api_signature(
    secret: bytes,
    verb: str,
    path: str,
    nonce: int | None = None,
    data: str = '',
) -> str:
    """Create a signature for exchange API requests
    
    Common pattern used by many exchanges.
    """
    if nonce:
        path = f'{path}?nonce={nonce}'
    
    message = f'{verb}{path}{data}'.encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return signature


def handle_unknown_asset(asset_name: str, location: Location) -> Asset | None:
    """Handle unknown assets from exchanges
    
    Logs a warning and returns None for unknown assets.
    """
    try:
        return Asset(asset_name)
    except UnknownAsset:
        logger.warning(
            f'Found unknown {location} asset {asset_name}. '
            f'Ignoring its balance/trade/movement.',
        )
        return None


def deserialize_asset_from_exchange(
    asset_name: str,
    location: Location,
    name_mapper: Callable[[str], str] | None = None,
) -> Asset | None:
    """Deserialize an asset from an exchange
    
    Handles exchange-specific asset naming conventions.
    """
    if name_mapper:
        asset_name = name_mapper(asset_name)
    
    return handle_unknown_asset(asset_name, location)


def exchange_response_serialization_error(
    msg: str,
    data: Any,
) -> RemoteError:
    """Create a RemoteError for exchange response serialization failures"""
    return RemoteError(
        f'{msg}. Check logs for details',
    )


def paginated_query_loop(
    limit: int,
    offset: int,
    step_size: int,
    total: int | None = None,
) -> list[tuple[int, int]]:
    """Generate offset/limit pairs for paginated queries
    
    Returns a list of (offset, limit) tuples for paginated API calls.
    """
    pages = []
    current_offset = offset
    
    while True:
        current_limit = min(step_size, limit - len(pages) * step_size)
        if current_limit <= 0:
            break
            
        pages.append((current_offset, current_limit))
        current_offset += current_limit
        
        if total is not None and current_offset >= total:
            break
            
        if len(pages) * step_size >= limit:
            break
    
    return pages


def calculate_fee_asset_and_amount(
    trade_data: dict[str, Any],
    trade_type: TradeType,
    base_asset: Asset,
    quote_asset: Asset,
    amount: FVal,
    rate: FVal,
) -> tuple[Asset, FVal]:
    """Calculate fee asset and amount from trade data
    
    Common logic for determining fee currency and amount.
    """
    fee_currency_key = 'fee_currency'
    fee_amount_key = 'fee'
    
    fee_asset = None
    fee_amount = ZERO
    
    if fee_currency_key in trade_data:
        fee_asset_name = trade_data[fee_currency_key]
        fee_asset = handle_unknown_asset(fee_asset_name, Location.BINANCE)  # Adjust location
        
    if fee_amount_key in trade_data:
        try:
            fee_amount = deserialize_fee(trade_data[fee_amount_key])
        except DeserializationError as e:
            logger.warning(f'Failed to deserialize fee amount: {e}')
            fee_amount = ZERO
    
    # If no fee asset specified, infer from trade type
    if fee_asset is None:
        if trade_type == TradeType.BUY:
            fee_asset = base_asset
        else:
            fee_asset = quote_asset
    
    return fee_asset, fee_amount


def timestamp_to_date(timestamp: Timestamp) -> str:
    """Convert timestamp to ISO date string"""
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp))


class ExchangeRequestError(Exception):
    """Exception raised when exchange request fails"""
    pass


class ExchangeAuthError(ExchangeRequestError):
    """Exception raised when exchange authentication fails"""
    pass


def retry_with_backoff(
    retries: int = 3,
    backoff_in_seconds: float = 1.0,
    exponential: bool = True,
) -> Callable:
    """Decorator for retrying functions with exponential backoff
    
    Useful for handling transient network errors.
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            x = backoff_in_seconds
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except (RemoteError, ExchangeRequestError) as e:
                    if i == retries - 1:
                        raise
                    
                    logger.debug(
                        f'Attempt {i + 1}/{retries} failed for {func.__name__}: {e}. '
                        f'Retrying in {x}s...',
                    )
                    time.sleep(x)
                    
                    if exponential:
                        x *= 2
            
        return wrapper
    return decorator


def build_query_string(params: dict[str, Any]) -> str:
    """Build a query string from parameters, handling None values"""
    # Remove None values
    cleaned_params = {k: v for k, v in params.items() if v is not None}
    return urlencode(cleaned_params)


def parse_trading_pair(
    pair: str,
    delimiter: str = '',
    base_assets_map: dict[str, str] | None = None,
) -> tuple[Asset | None, Asset | None]:
    """Parse a trading pair into base and quote assets
    
    Handles various exchange formats for trading pairs.
    """
    if delimiter:
        parts = pair.split(delimiter)
        if len(parts) != 2:
            logger.warning(f'Invalid trading pair format: {pair}')
            return None, None
        base_str, quote_str = parts
    else:
        # Try to parse without delimiter using known base assets
        if base_assets_map:
            for base_str, quote_str in base_assets_map.items():
                if pair.startswith(base_str):
                    quote_str = pair[len(base_str):]
                    break
        else:
            # Fallback: assume 3-4 character base assets
            if len(pair) == 6:
                base_str = pair[:3]
                quote_str = pair[3:]
            elif len(pair) == 7:
                # Could be 3-4 or 4-3
                base_str = pair[:4]
                quote_str = pair[4:]
            else:
                logger.warning(f'Cannot parse trading pair: {pair}')
                return None, None
    
    base_asset = handle_unknown_asset(base_str, Location.CRYPTOCOM)  # Adjust location
    quote_asset = handle_unknown_asset(quote_str, Location.CRYPTOCOM)  # Adjust location
    
    return base_asset, quote_asset