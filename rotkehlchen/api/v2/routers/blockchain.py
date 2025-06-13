"""Blockchain router for blockchain-related endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from rotkehlchen.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.blockchain import BlockchainService
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.chain.constants import SUPPORTED_BLOCKCHAIN_TO_CHAINID
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import SupportedBlockchain

router = APIRouter()


class BlockchainResponse(BaseModel):
    """Response model for blockchain operations"""
    result: Any
    message: str = ''


class BlockchainAccountRequest(BaseModel):
    """Request model for adding blockchain accounts"""
    accounts: list[str] | None = None  # For bulk operations
    address: str | None = None  # For single operations
    label: str | None = None
    labels: list[str] | None = None
    tags: list[str] | None = None  # For single operations
    tags_list: list[list[str]] | None = None  # For bulk operations, renamed to avoid conflict

    @field_validator('accounts')
    @classmethod
    def validate_accounts(cls, v: list[str] | None, values) -> list[str] | None:
        """Validate account addresses"""
        if v is not None and not v:
            raise ValueError('At least one account must be provided')
        return v


class NodeRequest(BaseModel):
    """Request model for adding RPC node"""
    name: str
    endpoint: str
    weight: float = 1.0
    active: bool = True


class NodeUpdateRequest(BaseModel):
    """Request model for updating RPC node"""
    identifier: int
    name: str | None = None
    endpoint: str | None = None
    weight: float | None = None
    active: bool | None = None


class EVMTransactionRequest(BaseModel):
    """Request model for EVM transaction queries"""
    address: str | None = None
    from_timestamp: int = Field(0, ge=0)
    to_timestamp: int = Field(2147483647, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)

    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str | None) -> str | None:
        """Validate EVM address if provided"""
        if v:
            try:
                return string_to_evm_address(v)
            except ValueError as e:
                raise ValueError(f'Invalid EVM address: {e}') from e
        return v


def get_blockchain_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> BlockchainService:
    """Get blockchain service instance"""
    return BlockchainService(db_service)


@router.get('/supported')
async def get_supported_chains(
    _: Annotated[str, Depends(require_logged_in_user)],
) -> BlockchainResponse:
    """Get list of supported blockchains"""
    chains = [
        {
            'id': blockchain.value,
            'name': blockchain.name,
            'type': 'evm' if blockchain in SUPPORTED_BLOCKCHAIN_TO_CHAINID else 'bitcoin',
        }
        for blockchain in SupportedBlockchain
    ]

    return BlockchainResponse(result=chains)


@router.get('/{blockchain}/accounts')
async def get_blockchain_accounts(
    blockchain: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Get accounts for a specific blockchain"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    accounts = blockchain_service.get_blockchain_accounts(blockchain)

    return BlockchainResponse(
        result={
            'accounts': [
                {
                    'address': account.address,
                    'label': account.label,
                    'tags': account.tags,
                }
                for account in accounts
            ],
        },
    )


@router.post('/{blockchain}/accounts')
async def add_blockchain_accounts(
    blockchain: str,
    account_data: BlockchainAccountRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Add accounts for a specific blockchain"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    accounts = account_data.accounts or []
    labels = account_data.labels or []
    tags_list = account_data.tags_list or []
    
    added_accounts = blockchain_service.add_blockchain_accounts(
        blockchain=blockchain,
        accounts=accounts,
        labels=labels,
        tags=tags_list,
    )

    return BlockchainResponse(
        result={'accounts': added_accounts},
        message=f'Added {len(added_accounts)} accounts',
    )


@router.delete('/{blockchain}/accounts')
async def remove_blockchain_accounts(
    blockchain: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
    accounts: list[str] = Query(...),
) -> BlockchainResponse:
    """Remove accounts for a specific blockchain"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    removed_count = blockchain_service.remove_blockchain_accounts(
        blockchain=blockchain,
        accounts=accounts,
    )

    return BlockchainResponse(
        result={'removed': removed_count},
        message=f'Removed {removed_count} accounts',
    )


@router.patch('/{blockchain}/accounts')
async def edit_blockchain_accounts(
    blockchain: str,
    accounts_data: list[BlockchainAccountRequest],
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Edit accounts for a specific blockchain - Compatible with v1 PATCH /api/1/blockchains/<blockchain>/accounts"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    edited_accounts = []
    for account_data in accounts_data:
        edited = blockchain_service.edit_blockchain_account(
            blockchain=blockchain,
            address=account_data.address,
            label=account_data.label,
            tags=account_data.tags,
        )
        edited_accounts.append(edited)

    return BlockchainResponse(
        result={'accounts': edited_accounts},
        message=f'Edited {len(edited_accounts)} accounts',
    )


@router.get('/{blockchain}/nodes')
async def get_blockchain_nodes(
    blockchain: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Get RPC nodes for a specific blockchain - Compatible with v1 GET /api/1/blockchains/<blockchain>/nodes"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    nodes = blockchain_service.get_blockchain_nodes(blockchain)
    
    return BlockchainResponse(result={'nodes': nodes})


@router.put('/{blockchain}/nodes')
async def add_blockchain_node(
    blockchain: str,
    node_data: NodeRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Add RPC node for a specific blockchain - Compatible with v1 PUT /api/1/blockchains/<blockchain>/nodes"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    node = blockchain_service.add_blockchain_node(
        blockchain=blockchain,
        name=node_data.name,
        endpoint=node_data.endpoint,
        weight=node_data.weight,
        active=node_data.active,
    )
    
    return BlockchainResponse(
        result={'node': node},
        message='Node added successfully',
    )


@router.patch('/{blockchain}/nodes')
async def update_blockchain_node(
    blockchain: str,
    node_data: NodeUpdateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Update RPC node for a specific blockchain - Compatible with v1 PATCH /api/1/blockchains/<blockchain>/nodes"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    node = blockchain_service.update_blockchain_node(
        blockchain=blockchain,
        identifier=node_data.identifier,
        name=node_data.name,
        endpoint=node_data.endpoint,
        weight=node_data.weight,
        active=node_data.active,
    )
    
    return BlockchainResponse(
        result={'node': node},
        message='Node updated successfully',
    )


@router.delete('/{blockchain}/nodes')
async def delete_blockchain_node(
    blockchain: str,
    identifier: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Delete RPC node for a specific blockchain - Compatible with v1 DELETE /api/1/blockchains/<blockchain>/nodes"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    success = blockchain_service.delete_blockchain_node(blockchain, identifier)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Node not found',
        )
    
    return BlockchainResponse(
        result={'success': True},
        message='Node deleted successfully',
    )


@router.post('/{blockchain}/nodes')
async def connect_blockchain_node(
    blockchain: str,
    node_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Connect to RPC node for a specific blockchain - Compatible with v1 POST /api/1/blockchains/<blockchain>/nodes"""
    try:
        blockchain_enum = SupportedBlockchain(blockchain.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported blockchain: {blockchain}',
        ) from None

    result = blockchain_service.connect_blockchain_node(blockchain, node_id)
    
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get('error', 'Failed to connect to node'),
        )
    
    return BlockchainResponse(
        result=result,
        message='Connected to node successfully',
    )


@router.get('/evm/transactions')
async def get_evm_transactions(
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
    chain_id: int | None = Query(None),
    address: str | None = Query(None),
    from_timestamp: int = Query(0, ge=0),
    to_timestamp: int = Query(2147483647, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> BlockchainResponse:
    """Get EVM transactions with optional filtering"""
    validated_address = None
    if address:
        try:
            validated_address = string_to_evm_address(address)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid EVM address: {e}',
            ) from e

    transactions = blockchain_service.get_evm_transactions(
        chain_id=chain_id,
        address=validated_address,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        limit=limit,
        offset=offset,
    )

    return BlockchainResponse(
        result={
            'transactions': transactions,
            'total': len(transactions),
        },
    )


@router.post('/evm/transactions/decode')
async def decode_pending_transactions(
    chain_id: int,
    tx_hashes: list[str],
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain_service: Annotated[BlockchainService, Depends(get_blockchain_service)],
) -> BlockchainResponse:
    """Decode pending EVM transactions"""
    results = blockchain_service.decode_pending_transactions(
        chain_id=chain_id,
        tx_hashes=tx_hashes,
    )

    return BlockchainResponse(
        result=results,
        message=f'Decoded {len(results)} transactions',
    )
