"""Repository for managing tags."""
from typing import TYPE_CHECKING, Optional

from sqlmodel import select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.tag import Tag, TagMapping

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class TagRepository(BaseRepository[Tag]):
    """Repository for managing tags."""
    
    model = Tag
    
    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """Get a tag by its name."""
        query = select(self.model).where(self.model.name == name)
        result = self.session.exec(query).first()
        return result
    
    def create_tag(
        self,
        name: str,
        description: Optional[str] = None,
        background_color: str = 'ffffff',
        foreground_color: str = '000000',
    ) -> Tag:
        """Create a new tag."""
        tag_data = {
            'name': name,
            'description': description,
            'background_color': background_color,
            'foreground_color': foreground_color,
        }
        return self.create(tag_data)
    
    def update_tag(
        self,
        name: str,
        description: Optional[str] = None,
        background_color: Optional[str] = None,
        foreground_color: Optional[str] = None,
    ) -> Optional[Tag]:
        """Update an existing tag."""
        tag = self.get_tag_by_name(name)
        if not tag:
            return None
        
        if description is not None:
            tag.description = description
        if background_color is not None:
            tag.background_color = background_color
        if foreground_color is not None:
            tag.foreground_color = foreground_color
        
        self.session.add(tag)
        self.session.commit()
        return tag
    
    def delete_tag(self, name: str) -> bool:
        """Delete a tag and all its mappings."""
        tag = self.get_tag_by_name(name)
        if not tag:
            return False
        
        # Delete all mappings for this tag
        mappings_query = select(TagMapping).where(TagMapping.tag == name)
        mappings = self.session.exec(mappings_query).all()
        for mapping in mappings:
            self.session.delete(mapping)
        
        # Delete the tag itself
        self.session.delete(tag)
        self.session.commit()
        return True
    
    def add_tag_mapping(
        self,
        tag_name: str,
        object_reference: str,
    ) -> Optional[TagMapping]:
        """Add a tag to an object (e.g., blockchain account, transaction)."""
        # Verify tag exists
        tag = self.get_tag_by_name(tag_name)
        if not tag:
            return None
        
        # Check if mapping already exists
        existing_query = select(TagMapping).where(
            TagMapping.tag == tag_name,
            TagMapping.object_reference == object_reference,
        )
        if self.session.exec(existing_query).first():
            return None  # Mapping already exists
        
        # Create new mapping
        mapping = TagMapping(tag=tag_name, object_reference=object_reference)
        self.session.add(mapping)
        self.session.commit()
        return mapping
    
    def remove_tag_mapping(
        self,
        tag_name: str,
        object_reference: str,
    ) -> bool:
        """Remove a tag from an object."""
        query = select(TagMapping).where(
            TagMapping.tag == tag_name,
            TagMapping.object_reference == object_reference,
        )
        mapping = self.session.exec(query).first()
        
        if mapping:
            self.session.delete(mapping)
            self.session.commit()
            return True
        return False
    
    def get_tags_for_object(self, object_reference: str) -> list[Tag]:
        """Get all tags for a specific object."""
        # Get tag names from mappings
        mappings_query = select(TagMapping.tag).where(
            TagMapping.object_reference == object_reference
        )
        tag_names = list(self.session.exec(mappings_query).all())
        
        if not tag_names:
            return []
        
        # Get full tag objects
        tags_query = select(self.model).where(self.model.name.in_(tag_names))
        return list(self.session.exec(tags_query).all())
    
    def get_objects_by_tag(self, tag_name: str) -> list[str]:
        """Get all object references that have a specific tag."""
        query = select(TagMapping.object_reference).where(
            TagMapping.tag == tag_name
        )
        return list(self.session.exec(query).all())
    
    def get_blockchain_accounts_by_tag(
        self,
        tag_name: str,
        blockchain: Optional[str] = None,
    ) -> list[tuple[str, str]]:
        """Get blockchain accounts that have a specific tag.
        
        Returns list of (blockchain, address) tuples.
        """
        object_refs = self.get_objects_by_tag(tag_name)
        
        accounts = []
        for ref in object_refs:
            # Object references for blockchain accounts are formatted as "blockchain_address"
            parts = ref.split('_', 1)
            if len(parts) == 2:
                chain, address = parts
                if blockchain is None or chain == blockchain:
                    accounts.append((chain, address))
        
        return accounts