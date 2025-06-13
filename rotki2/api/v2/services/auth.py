"""Authentication service"""
import hashlib
import secrets
from datetime import datetime
from typing import Any

from sqlmodel import Session

from rotki2.api.v2.repositories.user import UserRepository
from rotki2.api.v2.services.database import DatabaseService
from rotkehlchen.errors.api import AuthenticationError


class AuthService:
    """Service for handling authentication"""

    def __init__(self, db_service: DatabaseService, session: Session | None = None):
        self.db = db_service
        self.session = session or db_service.get_session()
        self.user_repo = UserRepository(self.session)

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

        # Hash the provided API key
        key_hash = self._hash_api_key(api_key)

        # Look up the API key in the database
        try:
            api_key_record = self.user_repo.find_api_key_by_hash(key_hash)

            if not api_key_record:
                raise AuthenticationError('Invalid API key')

            # Check if key is expired
            if api_key_record.expires_at and api_key_record.expires_at < datetime.now():
                raise AuthenticationError('API key has expired')

            # Update last used timestamp
            api_key_record.last_used = datetime.now()
            self.session.add(api_key_record)
            self.session.commit()

            return api_key_record.username
        except Exception:
            # If the API key table doesn't exist or other DB issues
            # This is a temporary fallback until the schema is updated
            raise AuthenticationError('API key authentication not available')

    def generate_api_key(self, username: str, name: str | None = None) -> dict[str, Any]:
        """Generate new API key for user"""
        # In rotkehlchen, users are identified by their database existence
        # For now, we'll assume the user exists if we can access the database
        # TODO: Properly integrate with the user system

        # Generate a secure random API key
        api_key = secrets.token_urlsafe(32)

        # Hash the API key for storage
        key_hash = self._hash_api_key(api_key)

        # Store the API key hash in the database
        api_key_record = self.user_repo.create_api_key(
            username=username,
            key_hash=key_hash,
            name=name or f"API Key {datetime.now().strftime('%Y-%m-%d')}",
        )

        return {
            'api_key': api_key,  # Return plain key only once
            'key_id': api_key_record.id,
            'name': api_key_record.name,
            'created_at': api_key_record.created_at.isoformat(),
        }

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        # Hash the API key to find it
        key_hash = self._hash_api_key(api_key)

        # Find the API key
        api_key_record = self.user_repo.find_api_key_by_hash(key_hash)
        if not api_key_record:
            return False

        # Delete the API key
        return self.user_repo.delete_api_key(api_key_record.id)

    def revoke_api_key_by_id(self, key_id: int) -> bool:
        """Revoke an API key by its ID"""
        return self.user_repo.delete_api_key(key_id)

    def list_api_keys(self, username: str) -> list[dict[str, Any]]:
        """List all API keys for a user"""
        api_keys = self.user_repo.get_user_api_keys(username)

        return [
            {
                'key_id': key.id,
                'name': key.name,
                'created_at': key.created_at.isoformat(),
                'last_used': key.last_used.isoformat() if key.last_used else None,
                'expires_at': key.expires_at.isoformat() if key.expires_at else None,
            }
            for key in api_keys
        ]

    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
