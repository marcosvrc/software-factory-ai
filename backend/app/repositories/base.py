"""Repositório genérico assíncrono."""
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    def __init__(self, model: type[ModelT], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, entity_id: Any) -> ModelT | None:
        return await self.db.get(self.model, entity_id)

    async def list(self, **filters: Any) -> list[ModelT]:
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        return list((await self.db.execute(query)).scalars())

    async def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        await self.db.flush()
        return entity
