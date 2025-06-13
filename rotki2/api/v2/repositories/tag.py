"""Repository for managing tags."""
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlmodel import col

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.models import Tag, TagMapping

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TagRepository(AsyncBaseRepository[Tag]):
    """Repository for managing tags."""

    def __init__(self, session: 'AsyncSession') -> None:
        """Initialize repository."""
        super().__init__(session, Tag)

    async def get_tag_by_name(self, name: str) -> Tag | None:
        """Get a tag by its name."""
        result = await self.session.exec(
            select(Tag).where(col(Tag.name) == name)
        )
        return result.first()

    async def create_tag(
        self,
        name: str,
        description: str | None = None,
        background_color: str = 'ffffff',
        foreground_color: str = '000000',
    ) -> Tag:
        """Create a new tag."""
        tag = Tag(
            name=name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )
        return await self.create(tag)

    async def update_tag(
        self,
        name: str,
        description: str | None = None,
        background_color: str | None = None,
        foreground_color: str | None = None,
    ) -> Tag | None:
        """Update an existing tag."""
        tag = await self.get_tag_by_name(name)
        if not tag:
            return None

        if description is not None:
            tag.description = description
        if background_color is not None:
            tag.background_color = background_color
        if foreground_color is not None:
            tag.foreground_color = foreground_color

        self.session.add(tag)
        await self.session.commit()
        return tag

    async def delete_tag(self, name: str) -> bool:
        """Delete a tag and all its mappings."""
        tag = await self.get_tag_by_name(name)
        if not tag:
            return False

        # Delete all mappings for this tag
        result = await self.session.exec(
            select(TagMapping).where(col(TagMapping.tag_name) == name)
        )
        mappings = result.all()
        for mapping in mappings:
            await self.session.delete(mapping)

        # Delete the tag itself
        await self.session.delete(tag)
        await self.session.commit()
        return True

    async def add_tag_mapping(
        self,
        tag_name: str,
        object_reference: str,
    ) -> TagMapping | None:
        """Add a tag to an object (e.g., blockchain account, transaction)."""
        # Verify tag exists
        tag = await self.get_tag_by_name(tag_name)
        if not tag:
            return None

        # Check if mapping already exists
        result = await self.session.exec(
            select(TagMapping).where(
                col(TagMapping.tag_name) == tag_name,
                col(TagMapping.object_reference) == object_reference,
            )
        )
        if result.first():
            return None  # Mapping already exists

        # Create new mapping
        mapping = TagMapping(tag_name=tag_name, object_reference=object_reference)
        self.session.add(mapping)
        await self.session.commit()
        return mapping

    async def remove_tag_mapping(
        self,
        tag_name: str,
        object_reference: str,
    ) -> bool:
        """Remove a tag from an object."""
        result = await self.session.exec(
            select(TagMapping).where(
                col(TagMapping.tag_name) == tag_name,
                col(TagMapping.object_reference) == object_reference,
            )
        )
        mapping = result.first()

        if mapping:
            await self.session.delete(mapping)
            await self.session.commit()
            return True
        return False

    async def get_tags_for_object(self, object_reference: str) -> list[Tag]:
        """Get all tags for a specific object."""
        # Get tag names from mappings
        result = await self.session.exec(
            select(TagMapping.tag_name).where(
                col(TagMapping.object_reference) == object_reference
            )
        )
        tag_names = list(result.all())

        if not tag_names:
            return []

        # Get full tag objects
        tags_result = await self.session.exec(
            select(Tag).where(col(Tag.name).in_(tag_names))
        )
        return list(tags_result.all())

    async def get_objects_by_tag(self, tag_name: str) -> list[str]:
        """Get all object references that have a specific tag."""
        result = await self.session.exec(
            select(TagMapping.object_reference).where(
                col(TagMapping.tag_name) == tag_name
            )
        )
        return list(result.all())

    async def get_blockchain_accounts_by_tag(
        self,
        tag_name: str,
        blockchain: str | None = None,
    ) -> list[tuple[str, str]]:
        """Get blockchain accounts that have a specific tag.
        
        Returns list of (blockchain, address) tuples.
        """
        object_refs = await self.get_objects_by_tag(tag_name)

        accounts = []
        for ref in object_refs:
            # Object references for blockchain accounts are formatted as "blockchain_address"
            parts = ref.split('_', 1)
            if len(parts) == 2:
                chain, address = parts
                if blockchain is None or chain == blockchain:
                    accounts.append((chain, address))

        return accounts
