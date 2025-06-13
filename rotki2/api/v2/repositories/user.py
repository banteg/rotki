"""User repository for v2 API.

Handles all database operations related to users and authentication.
"""

from sqlmodel import Session, select

from rotki2.api.v2.repositories.base import BaseRepository
from rotki2.db.models.user.auth import ApiKey, UserAccount
from rotki2.db.models.user.models import Settings


class UserRepository(BaseRepository[UserAccount]):
    """Repository for user-related database operations."""

    def __init__(self, session: Session):
        super().__init__(session, UserAccount)

    def find_by_username(self, username: str) -> UserAccount | None:
        """Find user by username."""
        statement = select(UserAccount).where(
            UserAccount.username == username,
        )
        result = self.session.exec(statement)
        return result.first()

    def find_by(self, **kwargs) -> list[UserAccount]:
        """Find users by multiple criteria."""
        statement = select(UserAccount)

        for key, value in kwargs.items():
            if hasattr(UserAccount, key):
                statement = statement.where(getattr(UserAccount, key) == value)

        results = self.session.exec(statement)
        return list(results.all())

    def create_api_key(
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
        self.session.commit()
        self.session.refresh(api_key)
        return api_key

    def find_api_key_by_hash(self, key_hash: str) -> ApiKey | None:
        """Find API key by its hash."""
        statement = select(ApiKey).where(ApiKey.key_hash == key_hash)
        result = self.session.exec(statement)
        return result.first()

    def get_user_api_keys(self, username: str) -> list[ApiKey]:
        """Get all API keys for a user."""
        statement = select(ApiKey).where(ApiKey.username == username)
        results = self.session.exec(statement)
        return list(results.all())

    def delete_api_key(self, key_id: int) -> bool:
        """Delete an API key."""
        api_key = self.session.get(ApiKey, key_id)
        if api_key:
            self.session.delete(api_key)
            self.session.commit()
            return True
        return False

    def update_settings(self, username: str, settings: dict) -> Settings | None:
        """Update user settings."""
        # Update settings in the settings table
        for key, value in settings.items():
            statement = select(Settings).where(Settings.name == key)
            result = self.session.exec(statement)
            setting = result.first()

            if setting:
                setting.value = str(value)
            else:
                setting = Settings(name=key, value=str(value))
                self.session.add(setting)

        self.session.commit()
        return None  # Return None for now, can be enhanced later
