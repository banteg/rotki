"""DeFi router for DeFi protocol endpoints"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import (
    get_chains_aggregator,
    get_db_connection,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.defi import DeFiService
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
