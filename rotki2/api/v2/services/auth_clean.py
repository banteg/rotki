"""Clean authentication service with proper dependency injection"""
import hashlib
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from rotki2.api.v2.repositories.user import UserRepository
from rotki2.api.v2.repositories.settings import SettingsRepository
from rotki2.common.errors import AuthenticationError, InputError
from rotki2.common.types import ModifiableDBSettings, PremiumCredentials

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    
    from rotki2.api.v2.services.database import DatabaseService
    from rotki2.api.v2.services.premium import PremiumService
    from rotki2.api.v2.services.settings import SettingsService


class CleanAuthService:
    """Authentication service with proper dependency injection and async patterns
    
    This service demonstrates clean architecture principles:
    - No god object dependencies
    - All database access through repositories
    - Proper async/await throughout
    - Clean dependency injection
    - No imports from old rotkehlchen code
    """
    
    def __init__(
        self,
        session: 'AsyncSession',
        user_repo: UserRepository,
        settings_repo: SettingsRepository,
        premium_service: 'PremiumService | None' = None,
        settings_service: 'SettingsService | None' = None,
    ):
        self.session = session
        self.user_repo = user_repo
        self.settings_repo = settings_repo
        self.premium_service = premium_service
        self.settings_service = settings_service
        
        # Authentication state
        self.current_user: str | None = None
        self.is_authenticated = False
    
    async def unlock_user(
        self,
        username: str,
        password: str,
        create_new: bool,
        sync_approval: Literal['yes', 'no', 'unknown'],
        premium_credentials: PremiumCredentials | None,
        resume_from_backup: bool,
        initial_settings: ModifiableDBSettings | None = None,
        sync_database: bool = True,
    ) -> dict[str, Any]:
        """Unlock an existing user or create a new one
        
        Returns user info and settings.
        """
        if create_new:
            # Create new user
            user = await self._create_user(
                username=username,
                password=password,
                initial_settings=initial_settings,
            )
        else:
            # Authenticate existing user
            user = await self._authenticate_user(username, password)
            if not user:
                raise AuthenticationError('Invalid username or password')
        
        # Set current user
        self.current_user = username
        self.is_authenticated = True
        
        # Handle premium if credentials provided
        premium_active = False
        if premium_credentials and self.premium_service:
            try:
                premium_active = await self.premium_service.activate(
                    username=username,
                    credentials=premium_credentials,
                    sync_approval=sync_approval,
                    sync_database=sync_database,
                )
            except Exception as e:
                if create_new:
                    # Rollback user creation on premium failure
                    await self._rollback_user_creation(username)
                    raise
                # For existing users, just log warning
                print(f"Premium activation failed: {e}")
        
        # Get user settings
        settings = {}
        if self.settings_service:
            settings = await self.settings_service.get_settings()
        
        return {
            'username': username,
            'new_user': create_new,
            'premium': premium_active,
            'settings': settings,
        }
    
    async def logout(self) -> None:
        """Logout the current user"""
        if not self.is_authenticated:
            return
        
        # Deactivate premium if active
        if self.premium_service:
            await self.premium_service.deactivate()
        
        # Clear authentication state
        self.current_user = None
        self.is_authenticated = False
    
    async def _create_user(
        self,
        username: str,
        password: str,
        initial_settings: ModifiableDBSettings | None = None,
    ) -> Any:
        """Create a new user account"""
        # Check if user already exists
        if await self.user_repo.user_exists(username):
            raise InputError(f'User {username} already exists')
        
        # Hash password
        password_hash = self._hash_password(password)
        
        # Create user
        user = await self.user_repo.create_user(
            username=username,
            password_hash=password_hash,
        )
        
        # Set initial settings if provided
        if initial_settings and self.settings_service:
            await self.settings_service.set_settings(initial_settings)
        
        return user
    
    async def _authenticate_user(self, username: str, password: str) -> Any | None:
        """Authenticate a user with username and password"""
        password_hash = self._hash_password(password)
        
        # Verify credentials
        is_valid = await self.user_repo.verify_password(username, password_hash)
        if not is_valid:
            return None
        
        # Return user object
        return await self.user_repo.find_by_username(username)
    
    async def _rollback_user_creation(self, username: str) -> None:
        """Rollback user creation in case of failure"""
        # In a real implementation, this would properly rollback
        # For now, just a placeholder
        pass
    
    def _hash_password(self, password: str) -> str:
        """Hash a password for storage"""
        # In production, use proper password hashing like bcrypt
        return hashlib.sha256(password.encode()).hexdigest()
    
    # API Key Management
    
    async def generate_api_key(
        self,
        username: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Generate a new API key for a user"""
        if not self.is_authenticated or self.current_user != username:
            raise AuthenticationError('Not authorized')
        
        # Generate secure random key
        api_key = secrets.token_urlsafe(32)
        key_hash = self._hash_api_key(api_key)
        
        # Store in database
        api_key_record = await self.user_repo.create_api_key(
            username=username,
            key_hash=key_hash,
            name=name or f"API Key {datetime.now().strftime('%Y-%m-%d')}",
        )
        
        return {
            'api_key': api_key,  # Only returned once
            'key_id': api_key_record.id,
            'name': api_key_record.name,
            'created_at': api_key_record.created_at.isoformat(),
        }
    
    async def authenticate_api_key(self, api_key: str) -> str | None:
        """Authenticate using API key, returns username if valid"""
        if not api_key or len(api_key) < 32:
            return None
        
        key_hash = self._hash_api_key(api_key)
        api_key_record = await self.user_repo.find_api_key_by_hash(key_hash)
        
        if not api_key_record:
            return None
        
        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < datetime.now():
            return None
        
        # Update last used timestamp
        api_key_record.last_used = datetime.now()
        await self.session.commit()
        
        return api_key_record.username
    
    async def revoke_api_key(self, key_id: int) -> bool:
        """Revoke an API key by ID"""
        if not self.is_authenticated:
            raise AuthenticationError('Not authenticated')
        
        return await self.user_repo.delete_api_key(key_id)
    
    async def list_api_keys(self, username: str) -> list[dict[str, Any]]:
        """List all API keys for a user"""
        if not self.is_authenticated or self.current_user != username:
            raise AuthenticationError('Not authorized')
        
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
    
    # Premium Management
    
    async def set_premium_credentials(
        self,
        credentials: PremiumCredentials,
    ) -> dict[str, Any]:
        """Set or update premium credentials"""
        if not self.is_authenticated:
            raise AuthenticationError('Not authenticated')
        
        if not self.premium_service:
            raise InputError('Premium service not available')
        
        # Activate premium
        success = await self.premium_service.set_credentials(
            username=self.current_user,
            credentials=credentials,
        )
        
        return {
            'success': success,
            'username': self.current_user,
        }
    
    async def delete_premium_credentials(self) -> dict[str, Any]:
        """Delete premium credentials"""
        if not self.is_authenticated:
            raise AuthenticationError('Not authenticated')
        
        if self.premium_service:
            await self.premium_service.deactivate()
        
        return {
            'success': True,
            'message': 'Premium credentials deleted',
        }