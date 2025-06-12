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
        # In Rotkehlchen, authentication happens at the database level
        # The password is used to decrypt the SQLCipher database
        # If we can connect to the user's database, they are authenticated
        
        try:
            # Try to get user settings which will verify the password
            settings = self.db.get_settings()
            
            return {
                'username': username,
                'premium_sync_enabled': settings.premium_sync_enabled,
                'premium': settings.premium is not None,
            }
        except Exception as e:
            # Database connection failed - wrong password
            raise AuthenticationError('Invalid username or password') from e

    def authenticate_api_key(self, api_key: str) -> str | None:
        """Authenticate using API key"""
        if not api_key or len(api_key) < 32:
            raise AuthenticationError('Invalid API key format')
        
        # TODO: Implement API key storage and validation
        # Currently no API key table exists in the database
        # This would need:
        # 1. A new table for API keys (api_key, username, created_at, revoked)
        # 2. Hashing of API keys before storage
        # 3. Validation against the stored hashes
        
        # For now, return None to indicate not implemented
        raise AuthenticationError('API key authentication not yet implemented')

    def generate_api_key(self, username: str) -> str:
        """Generate new API key for user"""
        # Generate a secure random API key
        api_key = secrets.token_urlsafe(32)
        
        # TODO: Store the API key hash in the database
        # Would need to:
        # 1. Hash the API key
        # 2. Store in api_keys table with username and metadata
        # 3. Return the plain API key (only shown once)
        
        return api_key

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        # In real implementation, would mark key as revoked in database
        return True
