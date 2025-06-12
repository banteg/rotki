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
from rotkehlchen.types import ChecksumEvmAddress

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
                detail=f'Invalid address format: {str(e)}',
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
            detail=f'Failed to get module balances: {str(e)}',
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
                detail=f'Invalid address format: {str(e)}',
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
            detail=f'Failed to get module balances: {str(e)}',
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
            detail=f'Failed to get module stats: {str(e)}',
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
                detail=f'Invalid address format: {str(e)}',
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
            detail=f'Failed to get Liquity balances: {str(e)}',
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
                detail=f'Invalid address format: {str(e)}',
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
            detail=f'Failed to get Liquity staking: {str(e)}',
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
                detail=f'Invalid address format: {str(e)}',
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
            detail=f'Failed to get Liquity pool: {str(e)}',
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
            detail=f'Failed to get Liquity stats: {str(e)}',
        ) from e