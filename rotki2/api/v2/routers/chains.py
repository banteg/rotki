"""API endpoints for blockchain chain operations."""
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from rotki2.api.v2.dependencies import (
    get_chains_aggregator_service,
    require_logged_in_user,
)
from rotki2.common.types import ChecksumEvmAddress
from rotki2.services.chains.aggregator_service import ChainsAggregatorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chains", tags=["chains"])


# Request/Response models
class ChainBalanceResponse(BaseModel):
    """Response model for chain balance queries."""
    chain_id: int
    chain_name: str
    balances: dict[ChecksumEvmAddress, dict[str, str]]


class MultiChainBalanceResponse(BaseModel):
    """Response model for multi-chain balance queries."""
    results: list[ChainBalanceResponse]
    total_chains: int


class AddAccountsRequest(BaseModel):
    """Request model for adding blockchain accounts."""
    accounts: dict[int, list[ChecksumEvmAddress]] = Field(
        ...,
        description="Dict mapping chain_id to list of addresses",
        example={1: ["0x742d35Cc6634C0532925a3b844Bc9e7595f6A123"]},
    )


class AddAccountsResponse(BaseModel):
    """Response model for adding blockchain accounts."""
    added: dict[str, list[ChecksumEvmAddress]]
    errors: dict[str, list[dict[str, Any]]]


class DecodeTransactionsRequest(BaseModel):
    """Request model for decoding transactions."""
    transactions: dict[int, list[str]] = Field(
        ...,
        description="Dict mapping chain_id to list of transaction hashes",
    )


class TransactionHistoryResponse(BaseModel):
    """Response model for transaction history."""
    transactions: list[dict[str, Any]]
    total: int


@router.get("/supported")
async def get_supported_chains(
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> dict[str, dict[int, str]]:
    """Get list of supported blockchain chains."""
    return {"chains": chains_service.get_supported_chains()}


@router.get("/balances/{address}")
async def get_all_chain_balances(
    address: ChecksumEvmAddress,
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> dict[str, dict[str, str]]:
    """
    Get balances for an address across all supported chains.
    
    Returns native token balance and any tracked token balances.
    """
    try:
        balances = await chains_service.get_all_balances(address)
        return balances
    except Exception as e:
        logger.error(f"Failed to get balances for {address}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query balances: {str(e)}",
        )


@router.post("/balances/query")
async def query_chain_balances(
    addresses: dict[int, list[ChecksumEvmAddress]],
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> MultiChainBalanceResponse:
    """
    Query balances for multiple addresses across specified chains.
    
    Request body should map chain_id to list of addresses.
    """
    try:
        results = await chains_service.query_balances(addresses)
        
        chain_results = []
        for chain_id, balances in results.items():
            chain_name = chains_service.get_supported_chains().get(
                chain_id, f"chain_{chain_id}"
            )
            chain_results.append(
                ChainBalanceResponse(
                    chain_id=chain_id,
                    chain_name=chain_name,
                    balances=balances,
                )
            )
        
        return MultiChainBalanceResponse(
            results=chain_results,
            total_chains=len(chain_results),
        )
        
    except Exception as e:
        logger.error(f"Failed to query balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query balances: {str(e)}",
        )


@router.get("/transactions/{address}")
async def get_transaction_history(
    address: ChecksumEvmAddress,
    chain_id: int | None = Query(None, description="Optional specific chain ID"),
    from_block: int | None = Query(None, description="Starting block number"),
    to_block: int | None = Query(None, description="Ending block number"),
    limit: int = Query(100, description="Maximum results", ge=1, le=1000),
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> TransactionHistoryResponse:
    """Get transaction history for an address."""
    try:
        transactions = await chains_service.get_transaction_history(
            address=address,
            chain_id=chain_id,
            from_block=from_block,
            to_block=to_block,
            limit=limit,
        )
        
        return TransactionHistoryResponse(
            transactions=transactions,
            total=len(transactions),
        )
        
    except Exception as e:
        logger.error(f"Failed to get transaction history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction history: {str(e)}",
        )


@router.post("/accounts/add")
async def add_blockchain_accounts(
    request: AddAccountsRequest,
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> AddAccountsResponse:
    """Add blockchain accounts to track across multiple chains."""
    try:
        result = await chains_service.add_blockchain_accounts(request.accounts)
        return AddAccountsResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to add accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add accounts: {str(e)}",
        )


@router.post("/accounts/remove")
async def remove_blockchain_accounts(
    request: AddAccountsRequest,
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> AddAccountsResponse:
    """Remove blockchain accounts from tracking."""
    try:
        result = await chains_service.remove_blockchain_accounts(request.accounts)
        return AddAccountsResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to remove accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove accounts: {str(e)}",
        )


@router.post("/transactions/decode")
async def decode_transactions(
    request: DecodeTransactionsRequest,
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> dict[str, Any]:
    """Decode transactions across multiple chains."""
    try:
        results = await chains_service.decode_transactions(request.transactions)
        return {"decoded": results}
        
    except Exception as e:
        logger.error(f"Failed to decode transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decode transactions: {str(e)}",
        )


@router.get("/ethereum/ens/{address}")
async def get_ens_name(
    address: ChecksumEvmAddress,
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> dict[str, str | None]:
    """Get ENS name for an Ethereum address."""
    try:
        names = await chains_service.get_ens_names([address])
        return {"address": address, "ens_name": names.get(address)}
        
    except Exception as e:
        logger.error(f"Failed to get ENS name: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ENS name: {str(e)}",
        )


@router.post("/ethereum/ens/batch")
async def get_ens_names_batch(
    addresses: list[ChecksumEvmAddress],
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> dict[ChecksumEvmAddress, str | None]:
    """Get ENS names for multiple Ethereum addresses."""
    try:
        return await chains_service.get_ens_names(addresses)
        
    except Exception as e:
        logger.error(f"Failed to get ENS names: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ENS names: {str(e)}",
        )


@router.get("/ethereum/eth2/deposits/{address}")
async def get_eth2_deposits(
    address: ChecksumEvmAddress,
    chains_service: Annotated[ChainsAggregatorService, Depends(get_chains_aggregator_service)],
    _: Annotated[str, Depends(require_logged_in_user)],
) -> dict[str, list[dict[str, Any]]]:
    """Get ETH2 deposits for an address."""
    try:
        deposits = await chains_service.get_eth2_deposits([address])
        return {"address": address, "deposits": deposits.get(address, [])}
        
    except Exception as e:
        logger.error(f"Failed to get ETH2 deposits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ETH2 deposits: {str(e)}",
        )