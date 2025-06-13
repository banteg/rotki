"""Async base repository class for v2 API.

Provides common async database operations and patterns for all repositories.
"""
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

T = TypeVar('T', bound=SQLModel)


class AsyncBaseRepository(ABC, Generic[T]):
    """Base async repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get(self, id: Any) -> T | None:
        """Get entity by ID."""
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Get all entities with pagination."""
        statement = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(statement)
        return [row[0] for row in result.all()]

    async def create(self, entity: T) -> T:
        """Create new entity."""
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T) -> T:
        """Update existing entity."""
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        entity = await self.get(id)
        if entity:
            self.session.delete(entity)
            await self.session.commit()
            return True
        return False

    async def count(self) -> int:
        """Count total entities."""
        statement = select(self.model)
        result = await self.session.execute(statement)
        return len(result.all())

    @abstractmethod
    async def find_by(self, **kwargs) -> list[T]:
        """Find entities by criteria. To be implemented by subclasses."""
