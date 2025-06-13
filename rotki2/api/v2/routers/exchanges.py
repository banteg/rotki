"""Exchanges router for exchange management endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from rotki2.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotki2.api.v2.services.database import DatabaseService
from rotki2.api.v2.services.exchanges import ExchangeService
from rotkehlchen.types import ApiKey, ApiSecret, Location
from rotkehlchen.utils.misc import ts_now

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
        # Try to convert to Location enum to validate
        try:
            Location(v)
        except ValueError:
            raise ValueError(f'Invalid exchange location: {v}')
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
    # TODO: Pass exchange_manager once it's part of app state
    return ExchangeService(
        session=db_service.session,
        db_service=db_service,
        exchange_manager=None,  # Will be injected from app state
    )


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
        result = await exchange_service.setup_exchange(
            name=exchange_data.name,
            location=Location(exchange_data.location),
            api_key=ApiKey(exchange_data.api_key),
            api_secret=ApiSecret(exchange_data.api_secret),
            passphrase=exchange_data.passphrase,
            kraken_account_type=exchange_data.kraken_account_type,
            binance_selected_trade_pairs=exchange_data.binance_markets,
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
    # Need to determine location from name
    exchanges = exchange_service.get_configured_exchanges()
    exchange = next((e for e in exchanges if e.name == name), None)
    
    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Exchange not found',
        )
    
    success, msg = await exchange_service.remove_exchange(
        name=name,
        location=Location(exchange.location),
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg or 'Failed to remove exchange',
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
    balances = await exchange_service.get_all_exchange_balances(ignore_cache=ignore_cache)

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
        success, msg = await exchange_service.edit_exchange(
            name=edit_data.name,
            location=Location(edit_data.location),
            new_name=edit_data.new_name,
            api_key=ApiKey(edit_data.api_key) if edit_data.api_key else None,
            api_secret=ApiSecret(edit_data.api_secret) if edit_data.api_secret else None,
            passphrase=edit_data.passphrase,
            kraken_account_type=edit_data.kraken_account_type,
            binance_selected_trade_pairs=edit_data.binance_markets,
        )
        
        if not success:
            raise ValueError(msg)

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
    pairs = await exchange_service.get_binance_pairs()

    return ExchangeResponse(result={'pairs': pairs})


@router.get('/binance/pairs/{name}')
async def get_user_binance_pairs(
    name: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Get user-configured Binance pairs - Compatible with v1 GET /api/1/exchanges/binance/pairs/<name>"""
    user_pairs = await exchange_service.get_user_binance_pairs(name)

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


# Margin trading endpoints
@router.get('/margin/positions')
async def get_all_margin_positions(
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> ExchangeResponse:
    """Get all margin positions across all exchanges"""
    # Would need to query all configured exchanges for margin positions
    all_positions = []
    exchanges = exchange_service.get_configured_exchanges()
    
    for exchange in exchanges:
        try:
            location_enum = Location(exchange.location)
            positions = await exchange_service.query_margin_positions(
                name=exchange.name,
                location=location_enum,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )
            all_positions.extend(positions)
        except Exception:
            # Skip exchanges that don't support margin or have errors
            continue
    
    return ExchangeResponse(result={'positions': all_positions})


@router.get('/{location}/margin/positions')
async def get_exchange_margin_positions(
    location: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> ExchangeResponse:
    """Get margin positions for a specific exchange"""
    try:
        location_enum = Location(location)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid exchange location: {location}',
        )
    
    # Get exchange by location
    exchanges = exchange_service.get_configured_exchanges()
    exchange_names = [e.name for e in exchanges if e.location == location]
    
    if not exchange_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No configured exchange found for location: {location}',
        )
    
    all_positions = []
    for name in exchange_names:
        try:
            positions = await exchange_service.query_margin_positions(
                name=name,
                location=location_enum,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )
            all_positions.extend(positions)
        except Exception as e:
            # Log error but continue with other exchanges
            continue
    
    return ExchangeResponse(result={'positions': all_positions})


@router.post('/{location}/margin/positions/sync')
async def sync_margin_positions(
    location: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Sync margin positions from exchange"""
    try:
        location_enum = Location(location)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid exchange location: {location}',
        )
    
    # Get exchange by location and query fresh data
    exchanges = exchange_service.get_configured_exchanges()
    exchange_names = [e.name for e in exchanges if e.location == location]
    
    if not exchange_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No configured exchange found for location: {location}',
        )
    
    synced_count = 0
    for name in exchange_names:
        try:
            # Query latest margin positions
            positions = await exchange_service.query_margin_positions(
                name=name,
                location=location_enum,
                from_timestamp=0,
                to_timestamp=None,
            )
            synced_count += len(positions)
        except Exception:
            continue
    
    return ExchangeResponse(
        result={'synced_positions': synced_count},
        message=f'Synced {synced_count} margin positions',
    )


@router.get('/margin/summary')
async def get_margin_summary(
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> ExchangeResponse:
    """Get margin trading summary with P&L calculations"""
    # Query margin positions from all exchanges
    exchanges = exchange_service.get_configured_exchanges()
    all_positions = []
    
    for exchange in exchanges:
        try:
            location_enum = Location(exchange.location)
            positions = await exchange_service.query_margin_positions(
                name=exchange.name,
                location=location_enum,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )
            all_positions.extend(positions)
        except Exception:
            continue
    
    # Calculate summary statistics
    total_profit_loss = sum(
        float(p.profit_loss) for p in all_positions 
        if hasattr(p, 'profit_loss') and p.profit_loss
    )
    open_positions = [p for p in all_positions if not hasattr(p, 'close_time') or p.close_time is None]
    closed_positions = [p for p in all_positions if hasattr(p, 'close_time') and p.close_time is not None]
    
    summary = {
        'total_positions': len(all_positions),
        'open_positions': len(open_positions),
        'closed_positions': len(closed_positions),
        'total_profit_loss': str(total_profit_loss),
        'profit_loss_by_exchange': {},
    }
    
    # Group P&L by exchange
    for exchange in exchanges:
        exchange_positions = [
            p for p in all_positions 
            if hasattr(p, 'location') and p.location == exchange.location
        ]
        exchange_pnl = sum(
            float(p.profit_loss) for p in exchange_positions 
            if hasattr(p, 'profit_loss') and p.profit_loss
        )
        if exchange_pnl != 0:
            summary['profit_loss_by_exchange'][exchange.location] = str(exchange_pnl)
    
    return ExchangeResponse(result=summary)


# Exchange rates endpoints
@router.get('/{location}/rates/{pair}')
async def get_exchange_rate(
    location: str,
    pair: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    exchange_service: Annotated[ExchangeService, Depends(get_exchange_service)],
) -> ExchangeResponse:
    """Get current exchange rate for a trading pair"""
    try:
        location_enum = Location(location)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid exchange location: {location}',
        )
    
    # This would need to be implemented by querying the exchange
    # For now, return a placeholder
    return ExchangeResponse(
        result={
            'pair': pair,
            'rate': '1.0',
            'timestamp': ts_now(),
        },
        message='Exchange rate query not yet implemented',
    )
