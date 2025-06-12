"""Balances router for balance management endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import (
    get_chains_aggregator,
    get_database_service,
    get_exchange_manager,
    get_rotki_notifier,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.balances import BalancesService
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.exchanges.manager import ExchangeManager

router = APIRouter()


class BalanceResponse(BaseModel):
    """Response model for balance operations"""
    result: dict[str, Any]
    message: str = ''


class ManualBalanceRequest(BaseModel):
    """Request model for adding manual balances"""
    asset: str
    amount: str
    location: str
    tags: list[str] | None = None
    label: str | None = None


class HistoricalBalanceRequest(BaseModel):
    """Request model for historical balance queries"""
    timestamp: Timestamp
    asset: str | None = None
    location: str | None = None


def get_balances_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    chains_aggregator: Annotated['ChainsAggregator', Depends(get_chains_aggregator)],
    exchange_manager: Annotated['ExchangeManager', Depends(get_exchange_manager)],
    notifier: Annotated['RotkiNotifier', Depends(get_rotki_notifier)],
) -> BalancesService:
    """Get balances service instance"""
    return BalancesService(
        session=db_service.get_session(),
        chain_manager=chains_aggregator,
        exchange_manager=exchange_manager,
        notifier=notifier,
    )


@router.get('/')
async def get_all_balances(
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
    save_data: bool = Query(False),
) -> BalanceResponse:
    """Get all balances across all locations"""
    balances = balances_service.get_all_balances(save_data=save_data)

    return BalanceResponse(result=balances)


@router.get('/blockchains')
async def get_blockchain_balances(
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
    blockchain: str | None = Query(None),
) -> BalanceResponse:
    """Get blockchain balances"""
    blockchain_balances = balances_service._get_blockchain_balances()

    if blockchain:
        # Filter for specific blockchain
        location = Location(blockchain.upper())
        if location in blockchain_balances:
            result = {blockchain: blockchain_balances[location]}
        else:
            result = {}
    else:
        # Convert locations to strings for response
        result = {
            loc.value: balances
            for loc, balances in blockchain_balances.items()
        }

    return BalanceResponse(result={'balances': result})


@router.get('/exchanges')
async def get_exchange_balances(
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
    location: str | None = Query(None),
) -> BalanceResponse:
    """Get exchange balances"""
    exchange_balances = balances_service._get_exchange_balances()

    if location:
        # Filter for specific exchange
        loc = Location(location)
        if loc in exchange_balances:
            result = {location: exchange_balances[loc]}
        else:
            result = {}
    else:
        # Convert locations to strings for response
        result = {
            loc.value: balances
            for loc, balances in exchange_balances.items()
        }

    return BalanceResponse(result={'balances': result})


@router.get('/manual')
async def get_manual_balances(
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Get manually tracked balances"""
    manual_balances = balances_service._get_manual_balances()

    result = [
        {
            'identifier': balance.identifier,
            'asset': balance.asset.identifier,
            'amount': str(balance.amount),
            'location': balance.location.value,
            'tags': balance.tags,
            'label': balance.label,
        }
        for balance in manual_balances
    ]

    return BalanceResponse(result={'balances': result})


@router.post('/manual')
async def add_manual_balance(
    balance_data: ManualBalanceRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Add a manually tracked balance"""
    balance = balances_service.add_manual_balance(
        asset=Asset(balance_data.asset),
        amount=FVal(balance_data.amount),
        location=Location(balance_data.location),
        tags=balance_data.tags,
    )

    return BalanceResponse(
        result={
            'identifier': balance.identifier,
            'asset': balance.asset.identifier,
            'amount': str(balance.amount),
            'location': balance.location.value,
        },
        message='Manual balance added successfully',
    )


@router.post('/historical')
async def get_historical_balance(
    request: HistoricalBalanceRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Get historical balance at specific timestamp"""
    asset = Asset(request.asset) if request.asset else None
    location = Location(request.location) if request.location else None

    balance = balances_service.get_historical_balance(
        timestamp=request.timestamp,
        asset=asset,
        location=location,
    )

    return BalanceResponse(result=balance)
