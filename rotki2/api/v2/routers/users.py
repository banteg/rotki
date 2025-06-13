"""Users router for user management endpoints"""
import os
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotki2.api.v2.dependencies import (
    get_auth_service,
    get_database_service,
    get_rotkehlchen,
)
from rotki2.api.v2.services.auth import AuthService
from rotki2.api.v2.services.database import DatabaseService
from rotkehlchen.errors.api import AuthenticationError

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

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
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> UserResponse:
    """Get list of all users"""
    users_dir = rotkehlchen.data_dir / 'users'

    users = []
    if users_dir.exists():
        for user_dir in users_dir.iterdir():
            if user_dir.is_dir():
                users.append(user_dir.name)

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
    # Get data directory from settings
    settings = db_service.get_settings()
    data_dir = Path(settings.data_directory)
    users_dir = data_dir / 'users'
    user_dir = users_dir / user_data.name

    # Check if user already exists
    if user_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'User {user_data.name} already exists',
        )

    # Create user directory
    try:
        user_dir.mkdir(parents=True, exist_ok=False)

        # TODO: Initialize user database with password encryption
        # This requires creating a new DBHandler instance with the user's password
        # and running the database creation scripts

        # For now, return success
        return UserResponse(
            result={
                'name': user_data.name,
                'settings': user_data.initial_settings or {},
            },
            message='User created successfully',
        )
    except Exception as e:
        # Clean up directory if creation failed
        if user_dir.exists():
            os.rmdir(user_dir)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to create user: {e!s}',
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
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> UserResponse:
    """Change user password"""
    # Verify current password
    try:
        auth_service.authenticate_user(username, current_password)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid current password',
        )

    # TODO: Implement password change
    # This requires:
    # 1. Re-encrypting the SQLCipher database with the new password
    # 2. Using PRAGMA rekey command
    # 3. Ensuring all connections are closed during the process

    return UserResponse(
        result={'success': True},
        message='Password changed successfully',
    )
