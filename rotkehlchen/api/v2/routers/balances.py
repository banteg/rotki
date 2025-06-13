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


@router.get('/blockchains/{blockchain}')
async def get_specific_blockchain_balance(
    blockchain: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Get balances for a specific blockchain - Compatible with v1 GET /api/1/balances/blockchains/<blockchain>"""
    blockchain_balances = balances_service._get_blockchain_balances()
    
    location = Location(blockchain.upper())
    if location in blockchain_balances:
        result = {blockchain: blockchain_balances[location]}
    else:
        result = {}
    
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


@router.put('/manual')
async def add_manual_balances_bulk(
    balances_data: list[ManualBalanceRequest],
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Add multiple manually tracked balances - Compatible with v1 PUT /api/1/balances/manual"""
    added_balances = []
    
    for balance_data in balances_data:
        balance = balances_service.add_manual_balance(
            asset=Asset(balance_data.asset),
            amount=FVal(balance_data.amount),
            location=Location(balance_data.location),
            tags=balance_data.tags,
        )
        added_balances.append({
            'identifier': balance.identifier,
            'asset': balance.asset.identifier,
            'amount': str(balance.amount),
            'location': balance.location.value,
        })
    
    return BalanceResponse(
        result={'balances': added_balances},
        message=f'{len(added_balances)} manual balances added successfully',
    )


@router.patch('/manual')
async def edit_manual_balance(
    balance_data: ManualBalanceRequest,
    identifier: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Edit a manually tracked balance - Compatible with v1 PATCH /api/1/balances/manual"""
    balance = balances_service.edit_manual_balance(
        identifier=identifier,
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
        message='Manual balance updated successfully',
    )


@router.delete('/manual')
async def delete_manual_balances(
    identifiers: list[int],
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Delete manually tracked balances - Compatible with v1 DELETE /api/1/balances/manual"""
    deleted_count = balances_service.delete_manual_balances(identifiers)
    
    return BalanceResponse(
        result={'deleted': deleted_count},
        message=f'{deleted_count} manual balances deleted successfully',
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


# v1 compatibility endpoints for historical balances
@router.post('/historical')
async def get_historical_balance_v1(
    timestamp: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Get historical balance for all assets at a timestamp - Compatible with v1 POST /api/1/balances/historical"""
    balances = balances_service.get_historical_balance_for_all_assets(timestamp)
    
    return BalanceResponse(
        result={
            'assets': balances,
            'liabilities': {},  # TODO: Implement liabilities
            'net_usd': str(sum(FVal(b['usd_value']) for b in balances.values())),
        },
    )


@router.post('/historical/asset')
async def get_historical_asset_balance(
    asset: str,
    from_timestamp: int,
    to_timestamp: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Get historical amounts for a single asset - Compatible with v1 POST /api/1/balances/historical/asset"""
    amounts = balances_service.get_historical_asset_amounts(
        asset=Asset(asset),
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )
    
    return BalanceResponse(result={'entries': amounts})


@router.post('/historical/netvalue')
async def get_historical_netvalue(
    _: Annotated[str, Depends(require_logged_in_user)],
    balances_service: Annotated[BalancesService, Depends(get_balances_service)],
) -> BalanceResponse:
    """Get historical net value - Compatible with v1 POST /api/1/balances/historical/netvalue"""
    netvalue_data = balances_service.get_historical_netvalue()
    
    return BalanceResponse(
        result={
            'times': netvalue_data['times'],
            'data': netvalue_data['data'],
        },
    )
