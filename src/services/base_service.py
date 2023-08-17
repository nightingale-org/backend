from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo import ReadPreference
from pymongo import WriteConcern
from pymongo.read_concern import ReadConcern


class BaseService:
    def __init__(self, db_client: AsyncIOMotorClient):
        self.__db_client = db_client
        self._current_session: AsyncIOMotorClientSession | None = None

    @asynccontextmanager
    async def transaction(
        self,
        read_concern: ReadConcern | None = None,
        write_concern: WriteConcern | None = None,
        read_preference: ReadPreference | None = None,
        max_commit_time_ms: float | None = None,
    ) -> AbstractAsyncContextManager[AsyncIOMotorClientSession]:
        async with await self.__db_client.start_session() as s:
            async with s.start_transaction(
                read_concern, write_concern, read_preference, max_commit_time_ms
            ):
                self._current_session = s
                yield s
                self._current_session = None
