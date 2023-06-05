from __future__ import annotations

from fastapi import APIRouter

from src.api.v1 import relationships, users


def create_root_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1", redirect_slashes=False)
    router.include_router(users.router)
    router.include_router(relationships.router)
    return router
