"""FastAPI dependency injection"""
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from rotkehlchen.api.v2.services.auth import AuthService
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.errors.api import AuthenticationError


def get_db_connection(request: Request) -> DBConnection:
    """Get database connection from request state"""
    return request.app.state.db_connection


def get_db_session(request: Request) -> Session:
    """Get SQLModel session from request state"""
    return request.app.state.db_session


def get_database_service(
    db_connection: Annotated[DBConnection, Depends(get_db_connection)],
) -> DatabaseService:
    """Get database service instance"""
    return DatabaseService(db_connection)


def get_auth_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> AuthService:
    """Get authentication service instance"""
    return AuthService(db_service)


async def require_logged_in_user(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    """Dependency to ensure user is logged in"""
    # Check for session or API key authentication
    user = None

    # Try session authentication first
    if hasattr(request.app.state, 'current_user'):
        user = request.app.state.current_user

    # Try API key authentication
    if not user:
        api_key = request.headers.get('X-API-Key')
        if api_key:
            try:
                user = auth_service.authenticate_api_key(api_key)
            except AuthenticationError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid API key',
                ) from None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authenticated',
        )

    return user
