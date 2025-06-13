"""Base repository class for v2 API.

Provides common database operations and patterns for all repositories.
"""
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlmodel import Session, SQLModel, select

T = TypeVar('T', bound=SQLModel)


class BaseRepository(ABC, Generic[T]):
    """Base repository with common CRUD operations."""

    def __init__(self, session: Session, model: type[T]):
        self.session = session
        self.model = model

    def get(self, id: Any) -> T | None:
        """Get entity by ID."""
        return self.session.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Get all entities with pagination."""
        statement = select(self.model).offset(skip).limit(limit)
        results = self.session.exec(statement)
        return list(results.all())

    def create(self, entity: T) -> T:
        """Create new entity."""
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """Update existing entity."""
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        entity = self.get(id)
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return True
        return False

    def count(self) -> int:
        """Count total entities."""
        statement = select(self.model)
        return len(self.session.exec(statement).all())

    @abstractmethod
    def find_by(self, **kwargs) -> list[T]:
        """Find entities by criteria. To be implemented by subclasses."""
