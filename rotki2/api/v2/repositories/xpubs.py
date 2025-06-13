"""Repository for managing Bitcoin HD wallet extended public keys (xpubs)."""
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.xpubs import Xpub, XpubMapping
from rotki2.db.models.user.models import TagMapping

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
    
    async def get_last_consecutive_xpub_derived_indices(
        self,
        xpub: str,
        blockchain: str,
    ) -> dict[int, int]:
        """Get the last consecutive derived indices for an xpub.
        
        Returns:
            Dict mapping derivation path (0=receiving, 1=change) to last index
        """
        # Query for both receiving (0) and change (1) addresses
        query = text("""
            SELECT 
                derivation_index % 2147483648 as path_type,
                MAX(derivation_index / 2147483648) as max_index
            FROM xpub_mappings
            WHERE xpub = :xpub AND blockchain = :blockchain
            GROUP BY path_type
        """)
        
        result = await self.session.execute(query, {
            'xpub': xpub,
            'blockchain': blockchain,
        })
        
        indices = {0: -1, 1: -1}  # Default to -1 for no addresses
        for row in result.fetchall():
            indices[row[0]] = row[1]
            
        return indices
    
    async def ensure_xpub_mappings_exist(
        self,
        xpub: str,
        addresses: list[tuple[str, str, int]],
    ) -> None:
        """Ensure xpub mappings exist for given addresses.
        
        Args:
            xpub: The extended public key
            addresses: List of (address, blockchain, derivation_index) tuples
        """
        for address, blockchain, derivation_index in addresses:
            existing = await self.get_xpub_for_address(address, blockchain)
            
            if not existing:
                await self.add_mapping(
                    xpub=xpub,
                    address=address,
                    blockchain=blockchain,
                    derivation_index=derivation_index,
                )
    
    async def get_addresses_to_xpub_mapping(
        self,
        addresses: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Get mapping from addresses to their parent xpub data.
        
        Args:
            addresses: Optional list of addresses to filter by
            
        Returns:
            Dict mapping address to xpub data (xpub, derivation_index, blockchain)
        """
        query = select(XpubMapping)
        
        if addresses:
            query = query.where(col(XpubMapping.address).in_(addresses))
            
        result = await self.session.exec(query)
        mappings = result.all()
        
        address_map = {}
        for mapping in mappings:
            address_map[mapping.address] = {
                'xpub': mapping.xpub,
                'derivation_index': mapping.derivation_index,
                'blockchain': mapping.blockchain,
            }
            
        return address_map
    
    async def add_xpub_with_tags(
        self,
        xpub: str,
        derivation_path: str | None = None,
        label: str | None = None,
        tags: list[str] | None = None,
    ) -> Xpub:
        """Add an xpub with optional tags.
        
        Args:
            xpub: The extended public key
            derivation_path: Optional derivation path
            label: Optional label
            tags: Optional list of tags
            
        Returns:
            Created Xpub instance
        """
        xpub_obj = await self.add_xpub(xpub, derivation_path, label)
        
        # Add tags if provided
        if tags:
            for tag in tags:
                mapping = TagMapping(
                    object_reference=f"xpub_{xpub}",
                    tag_name=tag,
                )
                self.session.add(mapping)
            await self.session.commit()
            
        return xpub_obj
    
    async def delete_xpub(
        self,
        xpub: str,
    ) -> bool:
        """Delete an xpub and all its mappings.
        
        Args:
            xpub: The extended public key to delete
            
        Returns:
            True if deleted, False if not found
        """
        xpub_obj = await self.get_by_xpub(xpub)
        
        if xpub_obj:
            # Delete mappings first
            await self.session.execute(
                text("DELETE FROM xpub_mappings WHERE xpub = :xpub"),
                {'xpub': xpub}
            )
            
            # Delete tags
            await self.session.execute(
                text("DELETE FROM tag_mappings WHERE object_reference = :ref"),
                {'ref': f'xpub_{xpub}'}
            )
            
            # Delete xpub
            await self.delete(xpub_obj)
            return True
            
        return False