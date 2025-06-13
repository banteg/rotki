"""Authentication router for auth-related endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import (
    get_auth_service,
    require_logged_in_user,
)
from rotki2.api.v2.services.auth import AuthService
from rotkehlchen.errors.api import AuthenticationError

router = APIRouter()


class LoginRequest(BaseModel):
    """Request model for user login"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Response model for successful login"""
    result: dict[str, Any]
    message: str = 'Login successful'


class APIKeyRequest(BaseModel):
    """Request model for API key generation"""
    name: str | None = None


class APIKeyResponse(BaseModel):
    """Response model for API key operations"""
    result: dict[str, Any]
    message: str = ''


@router.post('/login')
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    """Login with username and password"""
    try:
        user_data = auth_service.authenticate_user(request.username, request.password)
        return LoginResponse(result=user_data)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


@router.post('/api-keys')
async def create_api_key(
    request: APIKeyRequest,
    current_user: Annotated[str, Depends(require_logged_in_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIKeyResponse:
    """Generate a new API key for the current user"""
    try:
        api_key_data = auth_service.generate_api_key(current_user, request.name)
        return APIKeyResponse(
            result=api_key_data,
            message='API key generated successfully. Store it securely as it will not be shown again.',
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get('/api-keys')
async def list_api_keys(
    current_user: Annotated[str, Depends(require_logged_in_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIKeyResponse:
    """List all API keys for the current user"""
    api_keys = auth_service.list_api_keys(current_user)
    return APIKeyResponse(result={'api_keys': api_keys})


@router.delete('/api-keys/{key_id}')
async def revoke_api_key(
    key_id: int,
    current_user: Annotated[str, Depends(require_logged_in_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIKeyResponse:
    """Revoke an API key by ID"""
    # TODO: Verify the key belongs to the current user
    success = auth_service.revoke_api_key_by_id(key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='API key not found',
        )

    return APIKeyResponse(
        result={'success': True},
        message='API key revoked successfully',
    )
