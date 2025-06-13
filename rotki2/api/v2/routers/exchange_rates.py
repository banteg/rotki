"""Exchange rates router for currency conversion endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.exchange_rates import ExchangeRatesService
from rotkehlchen.types import Timestamp

router = APIRouter()


class ExchangeRatesResponse(BaseModel):
    """Response model for exchange rates operations"""
    result: dict[str, Any]
    message: str = ''


class ExchangeRatesRequest(BaseModel):
    """Request model for getting exchange rates"""
    currencies: list[str] | None = None
    target_currency: str = 'USD'
    timestamp: Timestamp | None = None


def get_exchange_rates_service() -> ExchangeRatesService:
    """Get exchange rates service instance"""
    return ExchangeRatesService()


@router.get('/')
async def get_exchange_rates(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ExchangeRatesService, Depends(get_exchange_rates_service)],
) -> ExchangeRatesResponse:
    """Get current exchange rates for fiat currencies"""
    rates = service.get_all_exchange_rates()

    return ExchangeRatesResponse(result=rates)


@router.post('/')
async def get_specific_exchange_rates(
    request_data: ExchangeRatesRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ExchangeRatesService, Depends(get_exchange_rates_service)],
) -> ExchangeRatesResponse:
    """Get exchange rates for specific currencies"""
    try:
        if request_data.timestamp:
            rates = service.get_historical_exchange_rates(
                currencies=request_data.currencies,
                target_currency=request_data.target_currency,
                timestamp=request_data.timestamp,
            )
        else:
            rates = service.get_exchange_rates(
                currencies=request_data.currencies,
                target_currency=request_data.target_currency,
            )

        return ExchangeRatesResponse(result=rates)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
