"""Exchanges router for exchange management endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from rotkehlchen.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.api.v2.services.exchanges import ExchangeService
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.types import Location

router = APIRouter()


class ExchangeResponse(BaseModel):
    """Response model for exchange operations"""
    result: Any
    message: str = ''


class ExchangeCredentialsRequest(BaseModel):
    """Request model for adding exchange credentials"""
    name: str
    location: str
    api_key: str
    api_secret: str
    passphrase: str | None = None
    kraken_account_type: str | None = None
    binance_markets: list[str] | None = None

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: str) -> str:
        """Validate exchange location"""
        if v not in SUPPORTED_EXCHANGES:
            raise ValueError(f'Unsupported exchange: {v}')
        return v


class ExchangeEditRequest(BaseModel):
    """Request model for editing exchange credentials"""
    name: str
    location: str
    new_name: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    passphrase: str | None = None
    kraken_account_type: str | None = None
    binance_markets: list[str] | None = None


class ExchangeBalanceQuery(BaseModel):
    """Query parameters for exchange balances"""
    ignore_cache: bool = False


def get_exchange_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> ExchangeService:
    """Get exchange service instance"""
    return ExchangeService(db_service)


@router.get('/')
async def get_configured_exchanges(
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Get list of configured exchanges"""
    exchanges = exchange_service.get_configured_exchanges()

    return ExchangeResponse(
        result={
            'exchanges': [
                {
                    'name': ex.name,
                    'location': ex.location,
                    'kraken_account_type': ex.kraken_account_type,
                    'binance_markets': ex.binance_markets,
                }
                for ex in exchanges
            ],
        },
    )


@router.post('/')
async def add_exchange(
    exchange_data: ExchangeCredentialsRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Add new exchange credentials"""
    try:
        result = exchange_service.add_exchange(
            name=exchange_data.name,
            location=Location(exchange_data.location),
            api_key=exchange_data.api_key,
            api_secret=exchange_data.api_secret,
            passphrase=exchange_data.passphrase,
            kraken_account_type=exchange_data.kraken_account_type,
            binance_markets=exchange_data.binance_markets,
        )

        return ExchangeResponse(
            result=result,
            message='Exchange added successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete('/{name}')
async def remove_exchange(
    name: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Remove exchange credentials"""
    success = exchange_service.remove_exchange(name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Exchange not found',
        )

    return ExchangeResponse(
        result={'success': True},
        message='Exchange removed successfully',
    )


@router.get('/balances')
async def get_all_exchange_balances(
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
    ignore_cache: bool = False,
) -> ExchangeResponse:
    """Get balances from all configured exchanges"""
    balances = exchange_service.get_all_exchange_balances(ignore_cache=ignore_cache)

    return ExchangeResponse(result=balances)


@router.get('/balances/{location}')
async def get_exchange_balances(
    location: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
    ignore_cache: bool = False,
) -> ExchangeResponse:
    """Get balances from specific exchange"""
    try:
        location_enum = Location(location)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid exchange location: {location}',
        )

    balances = exchange_service.get_exchange_balances(
        location=location_enum,
        ignore_cache=ignore_cache,
    )

    return ExchangeResponse(result=balances)


@router.post('/{location}/query')
async def query_exchange_data(
    location: str,
    query_type: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Query specific data from an exchange"""
    try:
        location_enum = Location(location)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid exchange location: {location}',
        )

    if query_type == 'trades':
        data = exchange_service.query_trades(location_enum)
    elif query_type == 'deposits':
        data = exchange_service.query_deposits(location_enum)
    elif query_type == 'withdrawals':
        data = exchange_service.query_withdrawals(location_enum)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid query type: {query_type}',
        )

    return ExchangeResponse(result=data)


@router.patch('/')
async def edit_exchange(
    edit_data: ExchangeEditRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Edit exchange credentials - Compatible with v1 PATCH /api/1/exchanges"""
    try:
        exchange_service.edit_exchange(
            name=edit_data.name,
            location=edit_data.location,
            new_name=edit_data.new_name,
            api_key=edit_data.api_key,
            api_secret=edit_data.api_secret,
            passphrase=edit_data.passphrase,
            kraken_account_type=edit_data.kraken_account_type,
            binance_markets=edit_data.binance_markets,
        )

        return ExchangeResponse(
            result={'success': True},
            message='Exchange updated successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete('/data')
async def purge_all_exchange_data(
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Purge all exchange data - Compatible with v1 DELETE /api/1/exchanges/data"""
    exchange_service.purge_all_exchange_data()

    return ExchangeResponse(
        result={'success': True},
        message='All exchange data purged successfully',
    )


@router.delete('/data/{location}')
async def purge_exchange_data(
    location: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Purge data for specific exchange - Compatible with v1 DELETE /api/1/exchanges/data/<location>"""
    try:
        location_enum = Location(location)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid exchange location: {location}',
        )

    exchange_service.purge_exchange_data(location_enum)

    return ExchangeResponse(
        result={'success': True},
        message=f'Exchange data purged for {location}',
    )


# Binance-specific endpoints
@router.get('/binance/pairs')
async def get_binance_pairs(
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Get all available Binance pairs - Compatible with v1 GET /api/1/exchanges/binance/pairs"""
    pairs = exchange_service.get_binance_pairs()

    return ExchangeResponse(result={'pairs': pairs})


@router.get('/binance/pairs/{name}')
async def get_user_binance_pairs(
    name: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Get user-configured Binance pairs - Compatible with v1 GET /api/1/exchanges/binance/pairs/<name>"""
    user_pairs = exchange_service.get_user_binance_pairs(name)

    return ExchangeResponse(result={'pairs': user_pairs})


@router.post('/{location}/savings')
async def get_exchange_savings_history(
    location: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
    from_timestamp: int = 0,
    to_timestamp: int = 2147483647,
) -> ExchangeResponse:
    """Get exchange savings history - Compatible with v1 POST /api/1/exchanges/<location>/savings"""
    try:
        location_enum = Location(location)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid exchange location: {location}',
        )

    history = exchange_service.get_exchange_savings_history(
        location=location_enum,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )

    return ExchangeResponse(result=history)


@router.post('/events/query')
async def query_exchange_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
    location: str,
    from_timestamp: int = 0,
    to_timestamp: int = 2147483647,
    event_type: str | None = None,
) -> ExchangeResponse:
    """Query history events for an exchange - Compatible with v1 POST /api/1/exchanges/events/query"""
    try:
        location_enum = Location(location)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid exchange location: {location}',
        )

    events = exchange_service.query_exchange_events(
        location=location_enum,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        event_type=event_type,
    )

    return ExchangeResponse(result={'events': events})
