"""Repository for user and exchange credentials."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.auth import UserCredential, UserCredentialMapping

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UserCredentialsRepository(AsyncBaseRepository[UserCredential]):
    """Repository for handling user credentials."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, UserCredential)

    async def get_by_name(self, name: str) -> UserCredential | None:
        """Get user credentials by name.
        
        Args:
            name: The credential name
            
        Returns:
            UserCredential if found, None otherwise
        """
        result = await self.session.exec(
            select(UserCredential).where(col(UserCredential.name) == name)
        )
        return result.first()

    async def get_by_service_and_user(
        self,
        service: str,
        username: str,
    ) -> UserCredential | None:
        """Get credentials for a specific service and username.
        
        Args:
            service: The service name (e.g., 'binance', 'kraken')
            username: The username for this service
            
        Returns:
            UserCredential if found, None otherwise
        """
        result = await self.session.exec(
            select(UserCredential).where(
                col(UserCredential.service) == service,
                col(UserCredential.name).contains(username),
            )
        )
        return result.first()

    async def list_by_service(self, service: str) -> list[UserCredential]:
        """List all credentials for a specific service.
        
        Args:
            service: The service name
            
        Returns:
            List of credentials for the service
        """
        result = await self.session.exec(
            select(UserCredential).where(
                col(UserCredential.service) == service
            )
        )
        return list(result.all())

    async def create_credential(
        self,
        name: str,
        service: str,
        api_key: str,
        api_secret: str | None = None,
        passphrase: str | None = None,
    ) -> UserCredential:
        """Create a new credential.
        
        Args:
            name: Unique credential name
            service: Service name
            api_key: API key
            api_secret: Optional API secret
            passphrase: Optional passphrase (for some exchanges)
            
        Returns:
            Created UserCredential instance
        """
        credential = UserCredential(
            name=name,
            service=service,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )
        return await self.create(credential)


class UserCredentialMappingsRepository(AsyncBaseRepository[UserCredentialMapping]):
    """Repository for handling user credential mappings."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, UserCredentialMapping)

    async def get_credentials_for_user(self, username: str) -> list[str]:
        """Get all credential names associated with a user.
        
        Args:
            username: The username
            
        Returns:
            List of credential names
        """
        result = await self.session.exec(
            select(UserCredentialMapping.credential_name).where(
                col(UserCredentialMapping.username) == username
            )
        )
        return list(result.all())

    async def add_mapping(
        self,
        username: str,
        credential_name: str,
    ) -> UserCredentialMapping:
        """Add a mapping between user and credential.
        
        Args:
            username: The username
            credential_name: The credential name
            
        Returns:
            Created UserCredentialMapping instance
        """
        mapping = UserCredentialMapping(
            username=username,
            credential_name=credential_name,
        )
        return await self.create(mapping)

    async def remove_mapping(
        self,
        username: str,
        credential_name: str,
    ) -> bool:
        """Remove a mapping between user and credential.
        
        Args:
            username: The username
            credential_name: The credential name
            
        Returns:
            True if removed, False if not found
        """
        result = await self.session.exec(
            select(UserCredentialMapping).where(
                col(UserCredentialMapping.username) == username,
                col(UserCredentialMapping.credential_name) == credential_name,
            )
        )
        mapping = result.first()
        
        if mapping:
            await self.delete(mapping)
            return True
        return False

    async def get_user_exchanges(self, username: str) -> list[str]:
        """Get all exchanges that a user has credentials for.
        
        Args:
            username: The username
            
        Returns:
            List of exchange service names
        """
        # First get all credential names for the user
        credential_names = await self.get_credentials_for_user(username)
        
        if not credential_names:
            return []
        
        # Then get unique services from those credentials
        result = await self.session.exec(
            select(UserCredential.service).where(
                col(UserCredential.name).in_(credential_names)
            ).distinct()
        )
        
        return list(result.all())

    async def delete_credential(self, name: str) -> bool:
        """Delete a credential and all its mappings.
        
        Args:
            name: The credential name
            
        Returns:
            True if deleted, False if not found
        """
        # First delete all mappings
        await self.session.exec(
            select(UserCredentialMapping).where(
                col(UserCredentialMapping.credential_name) == name
            ).delete()
        )
        
        # Then delete the credential
        result = await self.session.exec(
            select(UserCredential).where(
                col(UserCredential.name) == name
            )
        )
        credential = result.first()
        
        if credential:
            await self.delete(credential)
            return True
        return False