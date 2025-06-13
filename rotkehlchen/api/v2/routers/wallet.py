"""Wallet router for wallet operations"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.wallet import WalletService
from rotkehlchen.types import Timestamp

router = APIRouter()


class WalletResponse(BaseModel):
    """Response model for wallet operations"""
    result: dict[str, Any]
    message: str = ''


class WalletBalanceRequest(BaseModel):
    """Request model for wallet balance queries"""
    addresses: list[str]
    blockchain: str = 'ethereum'
    ignore_cache: bool = False


class InteractedAddressesRequest(BaseModel):
    """Request model for interacted addresses"""
    address: str
    blockchain: str = 'ethereum'


class TransferRequest(BaseModel):
    """Request model for token transfers"""
    from_address: str
    to_address: str
    blockchain: str = 'ethereum'
    token: str | None = None  # None for native transfers
    amount: str
    gas_price: str | None = None
    gas_limit: str | None = None


def get_wallet_service() -> WalletService:
    """Get wallet service instance"""
    return WalletService()


@router.get('/balance')
async def get_wallet_balance(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
    address: str,
    blockchain: str = 'ethereum',
) -> WalletResponse:
    """Get wallet balance for an address"""
    try:
        balance = service.get_balance(
            address=address,
            blockchain=blockchain,
        )
        
        return WalletResponse(result=balance)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post('/balance')
async def query_wallet_balances(
    request_data: WalletBalanceRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """Query wallet balances for multiple addresses"""
    try:
        balances = service.get_balances(
            addresses=request_data.addresses,
            blockchain=request_data.blockchain,
            ignore_cache=request_data.ignore_cache,
        )
        
        return WalletResponse(result=balances)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get('/interacted')
async def get_interacted_addresses(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
    address: str,
    blockchain: str = 'ethereum',
) -> WalletResponse:
    """Get addresses that have interacted with the given address"""
    try:
        interacted = service.get_interacted_addresses(
            address=address,
            blockchain=blockchain,
        )
        
        return WalletResponse(result=interacted)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post('/interacted')
async def post_interacted_addresses(
    request_data: InteractedAddressesRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """Get addresses that have interacted with the given address (POST)"""
    return await get_interacted_addresses(
        _,
        service,
        request_data.address,
        request_data.blockchain,
    )


@router.get('/transfer/native')
async def prepare_native_transfer(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
    from_address: str,
    to_address: str,
    amount: str,
    blockchain: str = 'ethereum',
) -> WalletResponse:
    """Prepare a native token transfer transaction"""
    try:
        tx_data = service.prepare_native_transfer(
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            blockchain=blockchain,
        )
        
        return WalletResponse(result=tx_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post('/transfer/native')
async def post_native_transfer(
    request_data: TransferRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """Prepare a native token transfer transaction (POST)"""
    if request_data.token is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Token must be null for native transfers',
        )
    
    return await prepare_native_transfer(
        _,
        service,
        request_data.from_address,
        request_data.to_address,
        request_data.amount,
        request_data.blockchain,
    )


@router.get('/transfer/token')
async def prepare_token_transfer(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
    from_address: str,
    to_address: str,
    token: str,
    amount: str,
    blockchain: str = 'ethereum',
) -> WalletResponse:
    """Prepare a token transfer transaction"""
    try:
        tx_data = service.prepare_token_transfer(
            from_address=from_address,
            to_address=to_address,
            token=token,
            amount=amount,
            blockchain=blockchain,
        )
        
        return WalletResponse(result=tx_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post('/transfer/token')
async def post_token_transfer(
    request_data: TransferRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """Prepare a token transfer transaction (POST)"""
    if request_data.token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Token is required for token transfers',
        )
    
    return await prepare_token_transfer(
        _,
        service,
        request_data.from_address,
        request_data.to_address,
        request_data.token,
        request_data.amount,
        request_data.blockchain,
    )