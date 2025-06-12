"""Authentication router for API key management"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import get_auth_service, require_logged_in_user
from rotkehlchen.api.v2.services.auth import AuthService

router = APIRouter()


class APIKeyResponse(BaseModel):
    """Response model for API key operations"""
    result: dict[str, str]


class APIKeyRequest(BaseModel):
    """Request model for API key operations"""
    name: str


@router.post('/api-keys')
async def create_api_key(
    request: APIKeyRequest,
    username: Annotated[str, Depends(require_logged_in_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIKeyResponse:
    """Generate a new API key for the authenticated user"""
    api_key = auth_service.generate_api_key(username)

    return APIKeyResponse(
        result={
            'api_key': api_key,
            'name': request.name,
        },
    )


@router.delete('/api-keys/{api_key}')
async def revoke_api_key(
    api_key: str,
    username: Annotated[str, Depends(require_logged_in_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIKeyResponse:
    """Revoke an API key"""
    success = auth_service.revoke_api_key(api_key)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='API key not found',
        )

    return APIKeyResponse(
        result={'message': 'API key revoked successfully'},
    )
