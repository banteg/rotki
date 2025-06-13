"""Periodic router for managing periodic data refresh and premium sync"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rotki2.api.v2.dependencies import require_logged_in_user
from rotki2.api.v2.services.periodic import PeriodicService

router = APIRouter()


class PeriodicResponse(BaseModel):
    """Response model for periodic operations"""
    result: dict[str, Any]
    message: str = ''


class PeriodicDataRequest(BaseModel):
    """Request model for periodic data operations"""
    refresh_balances: bool = False
    refresh_blockchain: bool = False
    refresh_exchanges: bool = False
    refresh_nfts: bool = False
    refresh_defi: bool = False


def get_periodic_service() -> PeriodicService:
    """Get periodic service instance"""
    return PeriodicService()


@router.get('/')
async def get_periodic_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    periodic: Annotated[PeriodicService, Depends(get_periodic_service)],
) -> PeriodicResponse:
    """Get status of periodic data refresh"""
    status = periodic.get_periodic_status()

    return PeriodicResponse(
        result={
            'status': status,
            'last_refresh': periodic.get_last_refresh_times(),
        },
    )


@router.post('/')
async def trigger_periodic_refresh(
    refresh_data: PeriodicDataRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    periodic: Annotated[PeriodicService, Depends(get_periodic_service)],
) -> PeriodicResponse:
    """Trigger periodic data refresh"""
    tasks_started = []

    if refresh_data.refresh_balances:
        task_id = periodic.refresh_balances()
        tasks_started.append({'type': 'balances', 'task_id': task_id})

    if refresh_data.refresh_blockchain:
        task_id = periodic.refresh_blockchain()
        tasks_started.append({'type': 'blockchain', 'task_id': task_id})

    if refresh_data.refresh_exchanges:
        task_id = periodic.refresh_exchanges()
        tasks_started.append({'type': 'exchanges', 'task_id': task_id})

    if refresh_data.refresh_nfts:
        task_id = periodic.refresh_nfts()
        tasks_started.append({'type': 'nfts', 'task_id': task_id})

    if refresh_data.refresh_defi:
        task_id = periodic.refresh_defi()
        tasks_started.append({'type': 'defi', 'task_id': task_id})

    if not tasks_started:
        return PeriodicResponse(
            result={'tasks': []},
            message='No refresh tasks requested',
        )

    return PeriodicResponse(
        result={'tasks': tasks_started},
        message=f'Started {len(tasks_started)} refresh tasks',
    )
