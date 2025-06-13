"""Tags repository for managing user tags."""
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotki2.db.models.user.models import Tag


class TagsRepository(AsyncBaseRepository[Tag]):
    """Repository for managing user tags."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Tag)

    async def add_tag(
        self,
        name: str,
        description: str | None = None,
        background_color: str | None = None,
        foreground_color: str | None = None,
    ) -> Tag:
        """Add a new tag."""
        tag = Tag(
            name=name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )
        self.session.add(tag)
        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def get_tag(self, name: str) -> Tag | None:
        """Get a tag by name."""
        stmt = select(Tag).where(Tag.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_tags(self) -> list[Tag]:
        """Get all tags."""
        stmt = select(Tag).order_by(Tag.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_tag(
        self,
        name: str,
        description: str | None = None,
        background_color: str | None = None,
        foreground_color: str | None = None,
    ) -> Tag | None:
        """Update an existing tag."""
        tag = await self.get_tag(name)
        if not tag:
            return None

        if description is not None:
            tag.description = description
        if background_color is not None:
            tag.background_color = background_color
        if foreground_color is not None:
            tag.foreground_color = foreground_color

        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def delete_tag(self, name: str) -> bool:
        """Delete a tag by name."""
        stmt = delete(Tag).where(Tag.name == name)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def find_by(self, **kwargs) -> list[Tag]:
        """Find tags by criteria."""
        stmt = select(Tag)
        
        for key, value in kwargs.items():
            if hasattr(Tag, key):
                stmt = stmt.where(getattr(Tag, key) == value)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())