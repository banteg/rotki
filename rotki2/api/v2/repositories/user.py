"""User repository for v2 API.

Handles all database operations related to users and authentication.
"""
from typing import TYPE_CHECKING

from sqlalchemy import select, text
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.auth import ApiKey, UserAccount
from rotki2.db.models.user.models import Settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository(AsyncBaseRepository[UserAccount]):
    """Repository for user-related database operations."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, UserAccount)

    async def find_by_username(self, username: str) -> UserAccount | None:
        """Find user by username."""
        result = await self.session.exec(
            select(UserAccount).where(
                col(UserAccount.username) == username
            )
        )
        return result.first()

    async def find_by(self, **kwargs) -> list[UserAccount]:
        """Find users by multiple criteria."""
        statement = select(UserAccount)

        for key, value in kwargs.items():
            if hasattr(UserAccount, key):
                statement = statement.where(getattr(UserAccount, key) == value)

        results = await self.session.exec(statement)
        return list(results.all())

    async def create_api_key(
        self,
        username: str,
        key_hash: str,
        name: str | None = None,
    ) -> ApiKey:
        """Create a new API key for a user."""
        from datetime import datetime

        api_key = ApiKey(
            username=username,
            key_hash=key_hash,
            name=name or 'API Key',
            created_at=datetime.now(),
        )
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key

    async def find_api_key_by_hash(self, key_hash: str) -> ApiKey | None:
        """Find API key by its hash."""
        result = await self.session.exec(
            select(ApiKey).where(col(ApiKey.key_hash) == key_hash)
        )
        return result.first()

    async def get_user_api_keys(self, username: str) -> list[ApiKey]:
        """Get all API keys for a user."""
        results = await self.session.exec(
            select(ApiKey).where(col(ApiKey.username) == username)
        )
        return list(results.all())

    async def delete_api_key(self, key_id: int) -> bool:
        """Delete an API key."""
        result = await self.session.exec(
            select(ApiKey).where(col(ApiKey.id) == key_id)
        )
        api_key = result.first()
        if api_key:
            await self.session.delete(api_key)
            await self.session.commit()
            return True
        return False

    async def update_settings(self, username: str, settings: dict) -> dict[str, Any]:
        """Update user settings.
        
        Returns:
            Updated settings dictionary
        """
        updated = {}
        
        # Update settings in the settings table
        for key, value in settings.items():
            # Use upsert pattern
            stmt = text(
                "INSERT INTO settings (name, value) VALUES (:name, :value) "
                "ON CONFLICT(name) DO UPDATE SET value = :value"
            )
            await self.session.execute(stmt, {"name": key, "value": str(value)})
            updated[key] = value

        await self.session.commit()
        return updated
    
    async def verify_password(self, username: str, password_hash: str) -> bool:
        """Verify user password.
        
        Args:
            username: The username
            password_hash: The password hash to verify
            
        Returns:
            True if password is correct, False otherwise
        """
        user = await self.find_by_username(username)
        if user is None:
            return False
        return user.password == password_hash
    
    async def get_all_users(self) -> list[UserAccount]:
        """Get all registered users."""
        result = await self.session.exec(select(UserAccount))
        return list(result.all())
    
    async def user_exists(self, username: str) -> bool:
        """Check if a user exists."""
        user = await self.find_by_username(username)
        return user is not None
    
    async def create_user(
        self,
        username: str,
        password_hash: str,
        premium_api_key: str | None = None,
        premium_api_secret: str | None = None,
    ) -> UserAccount:
        """Create a new user account."""
        user = UserAccount(
            username=username,
            password=password_hash,
            premium_api_key=premium_api_key,
            premium_api_secret=premium_api_secret,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
