"""Repository for external service credentials."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.services import ExternalServiceCredential

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ExternalServicesRepository(AsyncBaseRepository[ExternalServiceCredential]):
    """Repository for handling external service credentials."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, ExternalServiceCredential)

    async def get_by_service(self, service: str) -> ExternalServiceCredential | None:
        """Get credentials for a specific service.
        
        Args:
            service: The service name
            
        Returns:
            ExternalServiceCredential if found, None otherwise
        """
        result = await self.session.exec(
            select(ExternalServiceCredential).where(
                col(ExternalServiceCredential.service) == service
            )
        )
        return result.first()

    async def list_services(self) -> list[str]:
        """List all configured services.
        
        Returns:
            List of service names
        """
        result = await self.session.exec(
            select(ExternalServiceCredential.service).distinct()
        )
        return list(result.all())

    async def set_service_credentials(
        self,
        service: str,
        api_key: str,
    ) -> ExternalServiceCredential:
        """Set or update credentials for a service.
        
        Args:
            service: The service name
            api_key: The API key
            
        Returns:
            Created or updated ExternalServiceCredential
        """
        existing = await self.get_by_service(service)
        
        if existing:
            existing.api_key = api_key
            self.session.add(existing)
            await self.session.commit()
            return existing
        else:
            credential = ExternalServiceCredential(
                service=service,
                api_key=api_key,
            )
            return await self.create(credential)

    async def remove_service(self, service: str) -> bool:
        """Remove credentials for a service.
        
        Args:
            service: The service name
            
        Returns:
            True if removed, False if not found
        """
        credential = await self.get_by_service(service)
        
        if credential:
            await self.delete(credential)
            return True
        return False

    async def get_all_credentials(self) -> list[ExternalServiceCredential]:
        """Get all external service credentials.
        
        Returns:
            List of all external service credentials
        """
        result = await self.session.exec(select(ExternalServiceCredential))
        return list(result.all())