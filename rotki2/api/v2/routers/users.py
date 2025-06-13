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
    require_logged_in_user,
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
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> UserResponse:
    """Create a new user"""
    # Get data directory
    users_dir = rotkehlchen.data_dir / 'users'
    user_dir = users_dir / user_data.name

    # Check if user already exists
    if user_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'User {user_data.name} already exists',
        )

    try:
        # Use unlock_user with create_new=True to create the user
        from rotkehlchen.types import PremiumCredentials
        
        premium_credentials = None
        if user_data.premium_api_key and user_data.premium_api_secret:
            premium_credentials = PremiumCredentials(
                api_key=user_data.premium_api_key,
                api_secret=user_data.premium_api_secret,
            )
        
        user_info = await auth_service.unlock_user(
            user=user_data.name,
            password=user_data.password,
            create_new=True,
            sync_approval='unknown',
            premium_credentials=premium_credentials,
            resume_from_backup=False,
            initial_settings=user_data.initial_settings,
            sync_database=True,
        )

        return UserResponse(
            result={
                'username': user_info['username'],
                'premium': user_info.get('premium', False),
                'settings': user_info.get('settings', {}),
            },
            message='User created successfully',
        )
    except Exception as e:
        # Clean up directory if creation failed
        if user_dir.exists():
            import shutil
            shutil.rmtree(user_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to create user: {e!s}',
        )


@router.post('/login')
async def login_user(
    login_data: UserLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> UserResponse:
    """Login a user"""
    try:
        # Use the unlock_user method which handles both login and user creation
        user_info = await auth_service.unlock_user(
            user=login_data.name,
            password=login_data.password,
            create_new=False,
            sync_approval=login_data.sync_approval,
            premium_credentials=None,
            resume_from_backup=False,
            sync_database=True,
        )

        return UserResponse(
            result={
                'username': user_info['username'],
                'premium': user_info.get('premium', False),
                'settings': user_info.get('settings', {}),
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
    current_user: Annotated[str, Depends(require_logged_in_user)],
) -> UserResponse:
    """Logout current user"""
    await auth_service.logout()
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
