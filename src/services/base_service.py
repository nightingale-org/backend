from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncContextManager

from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorClientSession


class BaseService:
    def __init__(self, db_client: AsyncIOMotorClient):
        self.__db_client = db_client
        self._current_session: AsyncIOMotorClientSession | None = None

    @asynccontextmanager
    async def transaction(self) -> AsyncContextManager[AsyncIOMotorClientSession]:
        async with await self.__db_client.start_session() as s:
            async with s.start_transaction():
                self._current_session = s
                yield s
                self._current_session = None
