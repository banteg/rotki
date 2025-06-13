"""Authentication service"""
import hashlib
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.user import UserRepository
from rotki2.api.v2.services.database import DatabaseService
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.types import ModifiableDBSettings, PremiumCredentials

if TYPE_CHECKING:
    from rotki2.api.v2.services.premium import PremiumService
    from rotki2.api.v2.services.settings import SettingsService


class AuthService:
    """Service for handling authentication"""

    def __init__(
        self,
        db_service: DatabaseService,
        session: AsyncSession,
        premium_service: 'PremiumService | None' = None,
        settings_service: 'SettingsService | None' = None,
    ):
        self.db = db_service
        self.session = session
        self.user_repo = UserRepository(self.session)
        self.premium_service = premium_service
        self.settings_service = settings_service
        self.user_is_logged_in = False
        self.username: str | None = None

    async def authenticate_user(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate user with username and password"""
        # In Rotkehlchen, authentication happens at the database level
        # The password is used to decrypt the SQLCipher database
        # If we can connect to the user's database, they are authenticated

        try:
            # Verify password hash
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            is_valid = await self.user_repo.verify_password(username, password_hash)
            
            if not is_valid:
                raise AuthenticationError('Invalid username or password')

            # Get user info
            user = await self.user_repo.find_by_username(username)
            if not user:
                raise AuthenticationError('Invalid username or password')

            return {
                'username': username,
                'premium_sync_enabled': user.premium_api_key is not None,
                'premium': user.premium_api_key is not None,
            }
        except Exception as e:
            # Database connection failed - wrong password
            raise AuthenticationError('Invalid username or password') from e

    async def authenticate_api_key(self, api_key: str) -> str | None:
        """Authenticate using API key"""
        if not api_key or len(api_key) < 32:
            raise AuthenticationError('Invalid API key format')

        # Hash the provided API key
        key_hash = self._hash_api_key(api_key)

        # Look up the API key in the database
        try:
            api_key_record = await self.user_repo.find_api_key_by_hash(key_hash)

            if not api_key_record:
                raise AuthenticationError('Invalid API key')

            # Check if key is expired
            if api_key_record.expires_at and api_key_record.expires_at < datetime.now():
                raise AuthenticationError('API key has expired')

            # Update last used timestamp
            api_key_record.last_used = datetime.now()
            self.session.add(api_key_record)
            await self.session.commit()

            return api_key_record.username
        except Exception:
            # If the API key table doesn't exist or other DB issues
            # This is a temporary fallback until the schema is updated
            raise AuthenticationError('API key authentication not available')

    async def generate_api_key(self, username: str, name: str | None = None) -> dict[str, Any]:
        """Generate new API key for user"""
        # In rotkehlchen, users are identified by their database existence
        # For now, we'll assume the user exists if we can access the database
        # TODO: Properly integrate with the user system

        # Generate a secure random API key
        api_key = secrets.token_urlsafe(32)

        # Hash the API key for storage
        key_hash = self._hash_api_key(api_key)

        # Store the API key hash in the database
        api_key_record = await self.user_repo.create_api_key(
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

    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        # Hash the API key to find it
        key_hash = self._hash_api_key(api_key)

        # Find the API key
        api_key_record = await self.user_repo.find_api_key_by_hash(key_hash)
        if not api_key_record:
            return False

        # Delete the API key
        return await self.user_repo.delete_api_key(api_key_record.id)

    async def revoke_api_key_by_id(self, key_id: int) -> bool:
        """Revoke an API key by its ID"""
        return await self.user_repo.delete_api_key(key_id)

    async def list_api_keys(self, username: str) -> list[dict[str, Any]]:
        """List all API keys for a user"""
        api_keys = await self.user_repo.get_user_api_keys(username)

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

    async def unlock_user(
        self,
        user: str,
        password: str,
        create_new: bool,
        sync_approval: Literal['yes', 'no', 'unknown'],
        premium_credentials: PremiumCredentials | None,
        resume_from_backup: bool,
        initial_settings: ModifiableDBSettings | None = None,
        sync_database: bool = True,
    ) -> dict[str, Any]:
        """Unlocks an existing user or creates a new one if `create_new` is True
        
        This method migrates the core unlock logic from the old rotkehlchen.py
        but in an async-first approach.
        
        Returns a dict with:
        - username: The unlocked user's name
        - new_user: Whether this was a new user creation
        - premium: Whether premium is active
        - settings: The user's settings
        """
        self.username = user
        
        # Unlock or create the DB
        await self.db.unlock(
            username=user,
            password=password,
            create_new=create_new,
            initial_settings=initial_settings,
            resume_from_backup=resume_from_backup,
        )
        
        if create_new:
            # Perform actions for new database
            await self._perform_new_db_actions()
        
        # Initialize premium if credentials provided
        premium_active = False
        if self.premium_service:
            try:
                premium_active = await self.premium_service.try_premium_at_start(
                    given_premium_credentials=premium_credentials,
                    username=user,
                    create_new=create_new,
                    sync_approval=sync_approval,
                    sync_database=sync_database,
                )
            except Exception as e:
                # Only raise on new account creation with invalid premium
                if create_new and premium_credentials:
                    raise
                # Otherwise log warning and continue
                print(f"Warning: Could not authenticate premium credentials: {e}")
        
        # Get user settings
        settings = None
        if self.settings_service:
            settings = await self.settings_service.get_settings()
        
        self.user_is_logged_in = True
        
        return {
            'username': user,
            'new_user': create_new,
            'premium': premium_active,
            'settings': settings,
        }
    
    async def logout(self) -> None:
        """Logout the current user"""
        if not self.user_is_logged_in:
            return
            
        # Deactivate premium
        if self.premium_service:
            await self.premium_service.deactivate()
        
        # Clear database connection
        await self.db.logout()
        
        # Reset state
        self.user_is_logged_in = False
        self.username = None
    
    async def _perform_new_db_actions(self) -> None:
        """Perform actions needed for a newly created database"""
        # This would include initial data setup, migrations, etc.
        # For now, just a placeholder
        pass
    
    async def set_premium_credentials(self, credentials: PremiumCredentials) -> dict[str, Any]:
        """Set or update premium credentials for the logged-in user"""
        if not self.user_is_logged_in:
            raise AuthenticationError('No user is logged in')
            
        if not self.premium_service:
            raise AuthenticationError('Premium service not available')
            
        # Verify and activate premium
        await self.premium_service.set_credentials(credentials, self.username)
        
        # Save credentials to database
        await self.db.set_premium_credentials(credentials)
        
        return {
            'premium': True,
            'username': self.username,
        }
    
    async def delete_premium_credentials(self) -> dict[str, Any]:
        """Delete premium credentials for the logged-in user"""
        if not self.user_is_logged_in:
            raise AuthenticationError('No user is logged in')
            
        success = await self.db.delete_premium_credentials()
        
        if self.premium_service:
            await self.premium_service.deactivate()
        
        return {
            'success': success,
            'message': 'Premium credentials deleted' if success else 'Failed to delete premium credentials',
        }
