"""Base repository implementation with common CRUD operations"""

from abc import ABC
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from rotkehlchen.db.orm.base import Base

T = TypeVar('T', bound=Base)


class BaseRepository(ABC, Generic[T]):
    """Base repository with common CRUD operations"""

    def __init__(self, session: Session, model_class: type[T]):
        self.session = session
        self.model_class = model_class

    def get(self, **kwargs) -> T | None:
        """Get single entity by attributes"""
        stmt = select(self.model_class).filter_by(**kwargs)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all(self, **kwargs) -> list[T]:
        """Get all entities matching attributes"""
        stmt = select(self.model_class).filter_by(**kwargs)
        return list(self.session.execute(stmt).scalars().all())

    def exists(self, **kwargs) -> bool:
        """Check if entity exists"""
        stmt = select(self.model_class).filter_by(**kwargs).limit(1)
        return self.session.execute(stmt).scalar() is not None

    def count(self, **kwargs) -> int:
        """Count entities matching attributes"""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self.model_class).filter_by(**kwargs)
        return self.session.execute(stmt).scalar() or 0

    def add(self, entity: T) -> T:
        """Add new entity"""
        self.session.add(entity)
        self.session.flush()  # Flush to get ID without committing
        return entity

    def add_all(self, entities: list[T]) -> list[T]:
        """Add multiple entities"""
        self.session.add_all(entities)
        self.session.flush()
        return entities

    def update(self, entity: T) -> T:
        """Update existing entity"""
        self.session.merge(entity)
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        """Delete entity"""
        self.session.delete(entity)
        self.session.flush()

    def delete_by(self, **kwargs) -> int:
        """Delete entities by attributes, returns count deleted"""
        entities = self.get_all(**kwargs)
        for entity in entities:
            self.session.delete(entity)
        self.session.flush()
        return len(entities)
