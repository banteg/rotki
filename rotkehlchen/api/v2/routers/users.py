"""Users router for user management endpoints"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import get_auth_service, get_database_service
from rotkehlchen.api.v2.services.auth import AuthService
from rotkehlchen.api.v2.services.database import DatabaseService

router = APIRouter()


class UserCreateRequest(BaseModel):
    """Request model for creating a user"""
    name: str
    password: str
    premium_api_key: str | None = None
    premium_api_secret: str | None = None
    initial_settings: dict[str, Any] | None = None


class UserLoginRequest(BaseModel):
    """Request model for user login"""
    name: str
    password: str
    sync_approval: str = 'unknown'


class UserResponse(BaseModel):
    """Response model for user operations"""
    result: dict[str, Any]
    message: str = ''


@router.get('/')
async def get_users(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> UserResponse:
    """Get list of all users"""
    # In real implementation, would query users from database
    users = ['rotki_user']  # Mock data

    return UserResponse(
        result={'users': users},
    )


@router.post('/')
async def create_user(
    user_data: UserCreateRequest,
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Create a new user"""
    # Check if user already exists
    # In real implementation, would check database

    # Create user
    # In real implementation, would save to database

    return UserResponse(
        result={
            'name': user_data.name,
            'settings': user_data.initial_settings or {},
        },
        message='User created successfully',
    )


@router.post('/login')
async def login_user(
    login_data: UserLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Login a user"""
    try:
        user_info = auth_service.authenticate_user(
            username=login_data.name,
            password=login_data.password,
        )

        return UserResponse(
            result={
                'username': user_info['username'],
                'premium_sync_enabled': user_info.get('premium_sync_enabled', False),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post('/logout')
async def logout_user(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Logout current user"""
    return UserResponse(
        result={'success': True},
        message='User logged out successfully',
    )


@router.patch('/{username}/password')
async def change_password(
    username: str,
    current_password: str,
    new_password: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Change user password"""
    # Verify current password
    try:
        auth_service.authenticate_user(username, current_password)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid current password',
        )

    # Update password
    # In real implementation, would update in database

    return UserResponse(
        result={'success': True},
        message='Password changed successfully',
    )
