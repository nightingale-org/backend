from __future__ import annotations

from fastapi import APIRouter

from src.api.v1 import conversations
from src.api.v1 import relationships
from src.api.v1 import users


def create_root_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1", redirect_slashes=False)
    router.include_router(users.router)
    router.include_router(relationships.router)
    router.include_router(conversations.router)
    return router
