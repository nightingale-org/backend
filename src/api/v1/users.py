from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import EmailStr, parse_obj_as
from starlette.status import HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from src.api.auth_dependency import protected_route
from src.api.v1.schemas import (
    AccountScheme,
    UserInputSchema,
    UserOutputSchema,
    UserUpdateSchema,
)
from src.services.user_service import UserService
from src.utils.stub import DependencyStub

router = APIRouter(
    prefix="/users", tags=["users"], dependencies=[Depends(protected_route)]
)


@router.post(
    "/",
    status_code=201,
    summary="Create user",
    description="Create user",
    response_description="User created",
)
async def create_user(
    user: UserInputSchema,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
) -> UserOutputSchema:
    user = await user_service.create_user(**user.dict())
    return UserOutputSchema.from_orm(user)


@router.get("/connections/{email}/")
async def get_users_to_chat_with(
    email: EmailStr,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
) -> list[UserOutputSchema]:
    return parse_obj_as(
        list[UserOutputSchema], await user_service.get_users_to_chat_with(email)
    )


@router.patch(
    "/{user_id}/",
    status_code=HTTP_204_NO_CONTENT,
    summary="Update a user",
    description="Update user",
    response_description="User updated",
)
async def update_user(
    user_id: str,
    user_update_data: UserUpdateSchema,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    await user_service.update_user(user_id, **user_update_data.dict(exclude_none=True))
    return Response(status_code=HTTP_204_NO_CONTENT)


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
) -> UserOutputSchema:
    user = await user_service.get_user_by_filters(
        id=user_id,
        email=email,
        provider_account_id=provider_account_id,
    )
    if user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    return UserOutputSchema.from_orm(user)


@router.delete(
    "/{user_id}/",
    status_code=HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description="Delete a user",
    response_description="User deleted",
)
async def delete_user(
    user_id: str,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    await user_service.delete_user(user_id)
    return Response(status_code=HTTP_204_NO_CONTENT)


@router.post("/link/", status_code=200, summary="Link account")
async def link_account(
    account: AccountScheme,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    await user_service.link_account(account.user_id, account)
    return Response(status_code=200)


@router.post(
    "/unlink/{provider_name}/{provider_id}/", status_code=200, summary="Link account"
)
async def unlink_account(
    provider_name: str,
    provider_id: str,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    await user_service.unlink_account(provider_id, provider_name)
    return Response(status_code=200)
