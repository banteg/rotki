"""Authentication service"""
import hashlib
import secrets
from typing import Any

from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.errors.api import AuthenticationError


class AuthService:
    """Service for handling authentication"""

    def __init__(self, db_service: DatabaseService):
        self.db = db_service

    def authenticate_user(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate user with username and password"""
        # This is a simplified version - in real implementation would check against DB
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Check user credentials in database
        # For now, return a mock user
        return {
            'username': username,
            'premium_sync_enabled': True,
        }

    def authenticate_api_key(self, api_key: str) -> str | None:
        """Authenticate using API key"""
        # In real implementation, would check API key against database
        if not api_key or len(api_key) < 32:
            raise AuthenticationError('Invalid API key format')

        # Return username associated with API key
        return 'default_user'

    def generate_api_key(self, username: str) -> str:
        """Generate new API key for user"""
        return secrets.token_urlsafe(32)

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        # In real implementation, would mark key as revoked in database
        return True
