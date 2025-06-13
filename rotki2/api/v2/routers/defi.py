"""DeFi router for DeFi protocol endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import (
    get_chains_aggregator,
    get_db_connection,
    require_logged_in_user,
)
from rotki2.api.v2.services.defi import DeFiService
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.errors.misc import InputError
from rotkehlchen.premium.premium import premium_create_and_verify

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator

router = APIRouter()


class DeFiResponse(BaseModel):
    """Response model for DeFi operations"""
    result: dict[str, Any] | list[dict[str, Any]]
    message: str = ''


class AddressListRequest(BaseModel):
    """Request model for address list"""
    addresses: list[str] | None = None


def get_defi_service(
    db_connection: Annotated[DBConnection, Depends(get_db_connection)],
    chains_aggregator: Annotated['ChainsAggregator', Depends(get_chains_aggregator)],
) -> DeFiService:
    """Get DeFi service instance"""
    premium = premium_create_and_verify(db_connection)
    return DeFiService(
        db_connection=db_connection,
        chains_aggregator=chains_aggregator,
        premium=premium,
    )


@router.get('/metadata')
async def get_defi_metadata(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get metadata for all supported DeFi protocols"""
    protocols = service.get_defi_metadata()
    return DeFiResponse(result=protocols)


@router.get('/blockchains/{blockchain}/modules/{module}/balances')
async def get_module_balances(
    blockchain: str,
    module: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    addresses: list[str] | None = Query(None),
) -> DeFiResponse:
    """Get balances for a specific DeFi module"""
    # Parse addresses if provided
    parsed_addresses = None
    if addresses:
        try:
            parsed_addresses = [string_to_evm_address(addr) for addr in addresses]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid address format: {e!s}',
            ) from e

    try:
        result = service.get_module_balances(
            blockchain=blockchain,
            module_name=module,
            addresses=parsed_addresses,
        )
        return DeFiResponse(result=result)
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get module balances: {e!s}',
        ) from e


@router.get('/blockchains/{blockchain}/modules/{module}/v{version}/balances')
async def get_module_balances_versioned(
    blockchain: str,
    module: str,
    version: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    addresses: list[str] | None = Query(None),
) -> DeFiResponse:
    """Get balances for a specific version of a DeFi module"""
    # Parse addresses if provided
    parsed_addresses = None
    if addresses:
        try:
            parsed_addresses = [string_to_evm_address(addr) for addr in addresses]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid address format: {e!s}',
            ) from e

    try:
        result = service.get_module_balances(
            blockchain=blockchain,
            module_name=module,
            addresses=parsed_addresses,
            version=version,
        )
        return DeFiResponse(result=result)
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get module balances: {e!s}',
        ) from e


@router.get('/blockchains/{blockchain}/modules/{module}/stats')
async def get_module_stats(
    blockchain: str,
    module: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get statistics for a specific DeFi module"""
    if blockchain.upper() != 'ETH':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'DeFi modules are only supported on Ethereum, not {blockchain}',
        )

    try:
        result = service.get_module_stats(module_name=module)
        return DeFiResponse(result=result)
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get module stats: {e!s}',
        ) from e


# Liquity-specific endpoints
@router.get('/blockchains/eth/modules/liquity/balances')
async def get_liquity_balances(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    addresses: list[str] | None = Query(None),
) -> DeFiResponse:
    """Get Liquity trove positions"""
    parsed_addresses = None
    if addresses:
        try:
            parsed_addresses = [string_to_evm_address(addr) for addr in addresses]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid address format: {e!s}',
            ) from e

    try:
        result = service.get_liquity_balances(addresses=parsed_addresses)
        return DeFiResponse(result=result)
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get Liquity balances: {e!s}',
        ) from e


@router.get('/blockchains/eth/modules/liquity/staking')
async def get_liquity_staking(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    addresses: list[str] | None = Query(None),
) -> DeFiResponse:
    """Get Liquity staking positions"""
    parsed_addresses = None
    if addresses:
        try:
            parsed_addresses = [string_to_evm_address(addr) for addr in addresses]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid address format: {e!s}',
            ) from e

    try:
        result = service.get_liquity_staking(addresses=parsed_addresses)
        return DeFiResponse(result=result)
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get Liquity staking: {e!s}',
        ) from e


@router.get('/blockchains/eth/modules/liquity/pool')
async def get_liquity_pool(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    addresses: list[str] | None = Query(None),
) -> DeFiResponse:
    """Get Liquity stability pool positions"""
    parsed_addresses = None
    if addresses:
        try:
            parsed_addresses = [string_to_evm_address(addr) for addr in addresses]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid address format: {e!s}',
            ) from e

    try:
        result = service.get_liquity_pool(addresses=parsed_addresses)
        return DeFiResponse(result=result)
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get Liquity pool: {e!s}',
        ) from e


@router.get('/blockchains/eth/modules/liquity/stats')
async def get_liquity_stats(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get Liquity protocol statistics"""
    try:
        result = service.get_liquity_stats()
        return DeFiResponse(result=result)
    except InputError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get Liquity stats: {e!s}',
        ) from e


# v1 compatibility endpoints for DeFi modules
@router.delete('/blockchains/eth/modules/data')
async def purge_all_defi_data(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Purge all DeFi module data - Compatible with v1 DELETE /api/1/blockchains/eth/modules/data"""
    try:
        service.purge_all_module_data()
        return DeFiResponse(
            result={'success': True},
            message='All DeFi module data purged',
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to purge DeFi data: {e!s}',
        ) from e


@router.delete('/blockchains/eth/modules/{module_name}/data')
async def purge_module_data(
    module_name: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Purge data for a specific DeFi module - Compatible with v1 DELETE /api/1/blockchains/eth/modules/<module_name>/data"""
    try:
        service.purge_module_data(module_name)
        return DeFiResponse(
            result={'success': True},
            message=f'DeFi module {module_name} data purged',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to purge module data: {e!s}',
        ) from e


@router.get('/blockchains/eth/modules')
async def get_supported_modules(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get list of supported DeFi modules - Compatible with v1 GET /api/1/blockchains/eth/modules"""
    modules = service.get_supported_modules()
    return DeFiResponse(result={'modules': modules})


@router.get('/blockchains/eth/modules/liquity/balances')
async def get_liquity_balances_v1(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get Liquity trove positions - Compatible with v1 GET /api/1/blockchains/eth/modules/liquity/balances"""
    return await get_liquity_troves(_, service)


@router.get('/blockchains/eth/modules/liquity/staking')
async def get_liquity_staking_v1(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get Liquity staking positions - Compatible with v1 GET /api/1/blockchains/eth/modules/liquity/staking"""
    return await get_liquity_staking(_, service)


@router.get('/blockchains/eth/modules/liquity/pool')
async def get_liquity_pool_v1(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get Liquity stability pool positions - Compatible with v1 GET /api/1/blockchains/eth/modules/liquity/pool"""
    return await get_liquity_pool(_, service)


@router.get('/blockchains/eth/modules/{module}/balances')
async def get_module_balances(
    module: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get module balances - Compatible with v1 GET /api/1/blockchains/eth/modules/<module>/balances"""
    try:
        balances = service.get_module_balances(module)
        return DeFiResponse(result=balances)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get module balances: {e!s}',
        ) from e


@router.get('/blockchains/eth/modules/{module}/v{version}/balances')
async def get_module_balances_versioned(
    module: str,
    version: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get versioned module balances - Compatible with v1 GET /api/1/blockchains/eth/modules/<module>/v<version>/balances"""
    try:
        balances = service.get_module_balances_versioned(module, version)
        return DeFiResponse(result=balances)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get versioned module balances: {e!s}',
        ) from e


@router.get('/blockchains/eth/modules/{module}/stats')
async def get_module_stats(
    module: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get module statistics - Compatible with v1 GET /api/1/blockchains/eth/modules/<module>/stats"""
    try:
        stats = service.get_module_stats(module)
        return DeFiResponse(result=stats)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get module stats: {e!s}',
        ) from e


@router.get('/blockchains/eth/modules/pickle/dill')
async def get_pickle_dill(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get Pickle DILL balance - Compatible with v1 GET /api/1/blockchains/eth/modules/pickle/dill"""
    try:
        dill_balance = service.get_pickle_dill_balance()
        return DeFiResponse(result=dill_balance)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get Pickle DILL balance: {e!s}',
        ) from e


@router.get('/blockchains/eth/modules/loopring/balances')
async def get_loopring_balances(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
) -> DeFiResponse:
    """Get Loopring balances - Compatible with v1 GET /api/1/blockchains/eth/modules/loopring/balances"""
    try:
        balances = service.get_loopring_balances()
        return DeFiResponse(result=balances)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get Loopring balances: {e!s}',
        ) from e


# DeFi Events endpoints
@router.get('/events')
async def get_defi_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    protocol: str | None = Query(None, description="Filter by protocol"),
    account: str | None = Query(None, description="Filter by account address"),
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
    event_type: str | None = Query(None, description="Filter by event type"),
) -> DeFiResponse:
    """Get DeFi protocol events"""
    # This would use the history_events repository with DeFi filtering
    # For now, return placeholder
    return DeFiResponse(
        result={
            'events': [],
            'message': 'DeFi events query endpoint - implementation pending',
        },
    )


@router.get('/lending/summary')
async def get_lending_summary(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    protocol: str | None = Query(None, description="Filter by lending protocol"),
    account: str | None = Query(None, description="Filter by account address"),
) -> DeFiResponse:
    """Get lending protocol summary (deposits, borrows, health factor)"""
    # This would aggregate data from lending protocols like Aave, Compound
    return DeFiResponse(
        result={
            'deposits': {},
            'borrows': {},
            'health_factors': {},
            'message': 'Lending summary endpoint - implementation pending',
        },
    )


@router.get('/liquidity/positions')
async def get_liquidity_positions(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    protocol: str | None = Query(None, description="Filter by AMM protocol"),
    account: str | None = Query(None, description="Filter by account address"),
) -> DeFiResponse:
    """Get liquidity pool positions across DeFi protocols"""
    # This would query liquidity positions from Uniswap, Sushiswap, etc.
    return DeFiResponse(
        result={
            'positions': [],
            'message': 'Liquidity positions endpoint - implementation pending',
        },
    )


@router.get('/liquidity/events')
async def get_liquidity_events(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    account: str | None = Query(None, description="Filter by account address"),
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> DeFiResponse:
    """Get liquidity events (add/remove liquidity)"""
    # This would use history_events repository with liquidity event filtering
    return DeFiResponse(
        result={
            'events': [],
            'message': 'Liquidity events endpoint - implementation pending',
        },
    )


@router.get('/yield/summary')
async def get_yield_summary(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> DeFiResponse:
    """Get yield farming summary with APY calculations"""
    # This would calculate yield farming returns and APY
    return DeFiResponse(
        result={
            'total_yield': '0',
            'apy_by_protocol': {},
            'message': 'Yield summary endpoint - implementation pending',
        },
    )


# Cowswap-specific endpoints
@router.get('/cowswap/orders')
async def get_cowswap_orders(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    account: str | None = Query(None, description="Filter by account address"),
    status: str | None = Query(None, description="Filter by order status"),
) -> DeFiResponse:
    """Get Cowswap orders"""
    # This would use the cowswap_orders repository
    return DeFiResponse(
        result={
            'orders': [],
            'message': 'Cowswap orders endpoint - implementation pending',
        },
    )


@router.post('/cowswap/orders/sync')
async def sync_cowswap_orders(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    account: str,
) -> DeFiResponse:
    """Sync Cowswap orders for an account"""
    # This would trigger a background task to sync Cowswap orders
    return DeFiResponse(
        result={'task_id': 'placeholder-task-id'},
        message='Cowswap orders sync endpoint - implementation pending',
    )


# zkSync Lite endpoints
@router.get('/zksync-lite/transactions')
async def get_zksync_lite_transactions(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    address: str | None = Query(None, description="Filter by address"),
    tx_type: str | None = Query(None, description="Filter by transaction type"),
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> DeFiResponse:
    """Get zkSync Lite transactions"""
    # This would use the zksynclite repository
    return DeFiResponse(
        result={
            'transactions': [],
            'message': 'zkSync Lite transactions endpoint - implementation pending',
        },
    )


@router.get('/zksync-lite/swaps')
async def get_zksync_lite_swaps(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    address: str | None = Query(None, description="Filter by address"),
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> DeFiResponse:
    """Get zkSync Lite swaps"""
    # This would use the zksynclite swaps repository
    return DeFiResponse(
        result={
            'swaps': [],
            'message': 'zkSync Lite swaps endpoint - implementation pending',
        },
    )


# Gnosis Pay endpoints
@router.get('/gnosis-pay/transactions')
async def get_gnosis_pay_transactions(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    merchant: str | None = Query(None, description="Filter by merchant name"),
    country: str | None = Query(None, description="Filter by country"),
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> DeFiResponse:
    """Get Gnosis Pay transactions"""
    # This would use the gnosis_pay repository
    return DeFiResponse(
        result={
            'transactions': [],
            'message': 'Gnosis Pay transactions endpoint - implementation pending',
        },
    )


@router.get('/gnosis-pay/spending')
async def get_gnosis_pay_spending(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[DeFiService, Depends(get_defi_service)],
    group_by: str = Query('merchant', description="Group by: 'merchant' or 'category'"),
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
) -> DeFiResponse:
    """Get Gnosis Pay spending analytics"""
    # This would use the gnosis_pay repository spending analytics methods
    return DeFiResponse(
        result={
            'spending': [],
            'message': 'Gnosis Pay spending endpoint - implementation pending',
        },
    )
