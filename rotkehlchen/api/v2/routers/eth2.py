"""ETH2 staking router for Ethereum 2.0 staking endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.api.v2.services.eth2 import ETH2Service
from rotkehlchen.types import ChecksumEvmAddress, Timestamp

router = APIRouter()


class ValidatorRequest(BaseModel):
    """Request model for adding validators"""
    validator_index: int | None = None
    public_key: str | None = None
    ownership_proportion: str = "1.0"


class ETH2Response(BaseModel):
    """Response model for ETH2 operations"""
    result: dict[str, Any] | list[dict[str, Any]]
    message: str = ''


def get_eth2_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> ETH2Service:
    """Get ETH2 service instance"""
    return ETH2Service(db_service)


@router.get('/validators')
async def get_validators(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Get all tracked ETH2 validators"""
    validators = service.get_validators()
    return ETH2Response(result=validators)


@router.post('/validators')
async def add_validator(
    request: ValidatorRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Add a new ETH2 validator to track"""
    try:
        if request.validator_index is not None:
            validator_id = service.add_validator_by_index(
                index=request.validator_index,
                ownership_proportion=request.ownership_proportion,
            )
        elif request.public_key is not None:
            validator_id = service.add_validator_by_public_key(
                public_key=request.public_key,
                ownership_proportion=request.ownership_proportion,
            )
        else:
            raise ValueError("Either validator_index or public_key must be provided")
        
        return ETH2Response(
            result={'validator_id': validator_id},
            message='Validator added successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/validators/{validator_id}')
async def remove_validator(
    validator_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Remove a tracked ETH2 validator"""
    success = service.remove_validator(validator_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Validator not found',
        )
    
    return ETH2Response(
        result={'success': True},
        message='Validator removed successfully',
    )


@router.get('/stake/performance')
async def get_stake_performance(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
    from_timestamp: Timestamp = Query(default=0),
    to_timestamp: Timestamp | None = Query(default=None),
) -> ETH2Response:
    """Get ETH2 staking performance metrics"""
    performance = service.get_stake_performance(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )
    return ETH2Response(result=performance)


@router.get('/stake/daily-stats')
async def get_daily_stats(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
    from_timestamp: Timestamp = Query(default=0),
    to_timestamp: Timestamp | None = Query(default=None),
) -> ETH2Response:
    """Get daily ETH2 staking statistics"""
    stats = service.get_daily_stats(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
    )
    return ETH2Response(result=stats)


@router.get('/stake/deposits')
async def get_stake_deposits(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
    address: ChecksumEvmAddress | None = Query(default=None),
) -> ETH2Response:
    """Get ETH2 stake deposits"""
    deposits = service.get_stake_deposits(address=address)
    return ETH2Response(result=deposits)


# v1 compatibility endpoints
@router.put('/validators')
async def add_validator_v1(
    validator_index: int | None = None,
    public_key: str | None = None,
    ownership_proportion: str = "1.0",
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Add an ETH2 validator - Compatible with v1 PUT /api/1/blockchains/eth2/validators"""
    request = ValidatorRequest(
        validator_index=validator_index,
        public_key=public_key,
        ownership_proportion=ownership_proportion,
    )
    return await add_validator(request, _, service)


@router.patch('/validators')
async def edit_validator(
    validator_id: int,
    ownership_proportion: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Edit an ETH2 validator - Compatible with v1 PATCH /api/1/blockchains/eth2/validators"""
    try:
        service.edit_validator(validator_id, ownership_proportion)
        return ETH2Response(
            result={'success': True},
            message='Validator updated successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete('/validators')
async def delete_validator_v1(
    validator_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Delete an ETH2 validator - Compatible with v1 DELETE /api/1/blockchains/eth2/validators"""
    return await remove_validator(validator_id, _, service)


@router.put('/stake/performance')
async def get_stake_performance_v1(
    from_timestamp: Timestamp = 0,
    to_timestamp: Timestamp | None = None,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Get ETH2 staking performance - Compatible with v1 PUT /api/1/blockchains/eth2/stake/performance"""
    return await get_stake_performance(_, service, from_timestamp, to_timestamp)


@router.post('/stake/dailystats')
async def get_daily_stats_v1(
    from_timestamp: Timestamp = 0,
    to_timestamp: Timestamp | None = None,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Get ETH2 daily staking statistics - Compatible with v1 POST /api/1/blockchains/eth2/stake/dailystats"""
    return await get_daily_stats(_, service, from_timestamp, to_timestamp)


@router.put('/stake/events')
async def redecode_stake_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Redecode ETH2 block production events - Compatible with v1 PUT /api/1/blockchains/eth2/stake/events"""
    result = service.redecode_stake_events()
    return ETH2Response(
        result=result,
        message='ETH2 stake events reprocessing started',
    )


@router.delete('/stake/events')
async def reset_stake_data(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ETH2Service, Depends(get_eth2_service)],
) -> ETH2Response:
    """Reset ETH2 staking data - Compatible with v1 DELETE /api/1/blockchains/eth2/stake/events"""
    result = service.reset_stake_data()
    return ETH2Response(
        result=result,
        message='ETH2 staking data reset',
    )