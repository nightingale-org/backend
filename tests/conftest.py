from __future__ import annotations

import pytest

from _pytest.fixtures import SubRequest
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import app_config
from src.db.models import gather_documents


@pytest.fixture(scope="session")
def anyio_backend(request: SubRequest):
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def faker_session_locale() -> list[str]:
    return ["en_US"]


@pytest.fixture(scope="session")
async def motor_client() -> AsyncIOMotorClient:
    motor_client = AsyncIOMotorClient(str(app_config.db_url))
    yield motor_client
    await motor_client.drop_database(app_config.test_db_name)


@pytest.fixture(autouse=True, scope="session")
async def initialize_beanie(motor_client):
    await init_beanie(
        motor_client[app_config.test_db_name], document_models=gather_documents()
    )
