"""Repository for tag management"""


from sqlalchemy import delete, select

from rotkehlchen.db.orm.models import Tag, tag_mappings
from rotkehlchen.db.orm.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """Repository for managing tags and tag mappings"""

    def __init__(self, session):
        super().__init__(session, Tag)

    def get_tag(self, name: str) -> Tag | None:
        """Get a tag by name (case-insensitive)"""
        # Tags table has COLLATE NOCASE on name column
        return self.get(name=name)

    def create_tag(
        self,
        name: str,
        description: str | None = None,
        background_color: str | None = None,
        foreground_color: str | None = None,
    ) -> Tag:
        """Create a new tag"""
        tag = Tag(
            name=name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )
        return self.add(tag)

    def update_tag(
        self,
        name: str,
        description: str | None = None,
        background_color: str | None = None,
        foreground_color: str | None = None,
    ) -> Tag | None:
        """Update an existing tag"""
        tag = self.get_tag(name)
        if not tag:
            return None

        if description is not None:
            tag.description = description
        if background_color is not None:
            tag.background_color = background_color
        if foreground_color is not None:
            tag.foreground_color = foreground_color

        return self.update(tag)

    def delete_tag(self, name: str) -> bool:
        """Delete a tag and all its mappings"""
        tag = self.get_tag(name)
        if not tag:
            return False

        # Delete tag mappings first
        stmt = delete(tag_mappings).where(tag_mappings.c.tag_name == name)
        self.session.execute(stmt)

        # Delete the tag
        self.delete(tag)
        return True

    def ensure_tag_exists(
        self,
        name: str,
        description: str | None = None,
        background_color: str | None = None,
        foreground_color: str | None = None,
    ) -> Tag:
        """Ensure a tag exists, create if it doesn't"""
        tag = self.get_tag(name)
        if tag:
            return tag

        return self.create_tag(name, description, background_color, foreground_color)

    def get_all_tags(self) -> dict[str, Tag]:
        """Get all tags as a dictionary"""
        tags = self.get_all()
        return {tag.name: tag for tag in tags}

    # Tag mapping operations

    def add_tag_mapping(self, object_reference: str, tag_name: str) -> None:
        """Add a tag mapping"""
        stmt = tag_mappings.insert().values(
            object_reference=object_reference,
            tag_name=tag_name,
        )
        self.session.execute(stmt)
        self.session.flush()

    def remove_tag_mapping(self, object_reference: str, tag_name: str) -> bool:
        """Remove a specific tag mapping"""
        stmt = delete(tag_mappings).where(
            (tag_mappings.c.object_reference == object_reference) &
            (tag_mappings.c.tag_name == tag_name),
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount > 0

    def remove_tag_mappings(self, object_reference: str) -> int:
        """Remove all tag mappings for an object"""
        stmt = delete(tag_mappings).where(
            tag_mappings.c.object_reference == object_reference,
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def get_tags_for_object(self, object_reference: str) -> list[str]:
        """Get all tag names for an object"""
        stmt = select(tag_mappings.c.tag_name).where(
            tag_mappings.c.object_reference == object_reference,
        )
        return [row[0] for row in self.session.execute(stmt)]

    def get_mappings_by_tag(self, tag_name: str) -> list[str]:
        """Get all object references that have a specific tag"""
        stmt = select(tag_mappings.c.object_reference).where(
            tag_mappings.c.tag_name == tag_name,
        )
        return [row[0] for row in self.session.execute(stmt)]

    def replace_tag_mappings(
        self,
        object_reference: str,
        tag_names: list[str],
    ) -> None:
        """Replace all tag mappings for an object"""
        # Remove existing mappings
        self.remove_tag_mappings(object_reference)

        # Add new mappings
        for tag_name in tag_names:
            self.add_tag_mapping(object_reference, tag_name)
