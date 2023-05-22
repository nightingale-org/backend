from fastapi import APIRouter

from src.api.v1 import users


def create_root_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1", redirect_slashes=False)
    router.include_router(users.router)
    return router
