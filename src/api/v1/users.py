from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from starlette.status import HTTP_404_NOT_FOUND

from src.api.v1.schemas import AccountScheme, UserSchema
from src.db.models import User
from src.services.user_service import UserService
from src.utils.stub import DependencyStub

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    status_code=201,
    summary="Create user",
    description="Create user",
    response_description="User created",
    response_model_by_alias=False,
)
async def create_user(
    user: UserSchema,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
) -> User:
    return await user_service.create_user(**user.dict())


@router.get(
    "/",
    status_code=200,
    summary="Get user",
    description="Get user",
    response_description="User retrieved",
)
async def get_user_by_account(
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
    user_id: str | None = None,
    email: str | None = None,
    provider_account_id: str | None = None,
    provider_name: Annotated[str | None, Query(alias="provider")] = None,
) -> User:
    user = await user_service.get_user_by_filters(
        id=user_id,
        email=email,
        provider_account_id=provider_account_id,
        provider_name=provider_name,
    )
    if user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    return user


@router.delete(
    "/{user_id}/",
    status_code=200,
    summary="Get user",
    description="Delete user",
    response_description="User deleted",
)
async def delete_user(
    user_id: str,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    return await user_service.delete_user(user_id)


@router.post("/link/", status_code=200, summary="Link account")
async def link_account(
    account: AccountScheme,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    await user_service.link_account(account.user_id, account)
    return Response(status_code=200)
