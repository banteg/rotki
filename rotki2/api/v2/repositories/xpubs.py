"""Repository for managing Bitcoin HD wallet extended public keys (xpubs)."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.xpubs import Xpub, XpubMapping

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class XpubsRepository(AsyncBaseRepository[Xpub]):
    """Repository for handling Bitcoin HD wallet xpubs."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, Xpub)

    async def get_by_xpub(self, xpub: str) -> Xpub | None:
        """Get xpub details by the xpub string.
        
        Args:
            xpub: The extended public key string
            
        Returns:
            Xpub if found, None otherwise
        """
        result = await self.session.exec(
            select(Xpub).where(col(Xpub.xpub) == xpub)
        )
        return result.first()

    async def get_all_xpubs(self) -> list[Xpub]:
        """Get all registered xpubs.
        
        Returns:
            List of all xpubs
        """
        result = await self.session.exec(select(Xpub))
        return list(result.all())

    async def add_xpub(
        self,
        xpub: str,
        derivation_path: str | None = None,
        label: str | None = None,
    ) -> Xpub:
        """Add a new xpub.
        
        Args:
            xpub: The extended public key string
            derivation_path: Optional derivation path
            label: Optional label for the xpub
            
        Returns:
            Created Xpub instance
        """
        new_xpub = Xpub(
            xpub=xpub,
            derivation_path=derivation_path,
            label=label,
        )
        return await self.create(new_xpub)


class XpubMappingsRepository(AsyncBaseRepository[XpubMapping]):
    """Repository for handling xpub to address mappings."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, XpubMapping)

    async def get_addresses_for_xpub(
        self,
        xpub: str,
        blockchain: str | None = None,
    ) -> list[XpubMapping]:
        """Get all addresses derived from an xpub.
        
        Args:
            xpub: The extended public key
            blockchain: Optional blockchain filter
            
        Returns:
            List of xpub mappings
        """
        query = select(XpubMapping).where(col(XpubMapping.xpub) == xpub)
        
        if blockchain:
            query = query.where(col(XpubMapping.blockchain) == blockchain)
            
        result = await self.session.exec(query)
        return list(result.all())

    async def get_xpub_for_address(
        self,
        address: str,
        blockchain: str,
    ) -> XpubMapping | None:
        """Get the xpub mapping for a specific address.
        
        Args:
            address: The blockchain address
            blockchain: The blockchain identifier
            
        Returns:
            XpubMapping if found, None otherwise
        """
        result = await self.session.exec(
            select(XpubMapping).where(
                col(XpubMapping.address) == address,
                col(XpubMapping.blockchain) == blockchain,
            )
        )
        return result.first()

    async def add_mapping(
        self,
        xpub: str,
        address: str,
        blockchain: str,
        derivation_index: int,
    ) -> XpubMapping:
        """Add a new xpub to address mapping.
        
        Args:
            xpub: The extended public key
            address: The derived address
            blockchain: The blockchain identifier
            derivation_index: The derivation index used
            
        Returns:
            Created XpubMapping instance
        """
        mapping = XpubMapping(
            xpub=xpub,
            address=address,
            blockchain=blockchain,
            derivation_index=derivation_index,
        )
        return await self.create(mapping)