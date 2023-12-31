from __future__ import annotations

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Response
from fastapi import UploadFile
from starlette.status import HTTP_204_NO_CONTENT
from starlette.status import HTTP_404_NOT_FOUND

from src.schemas.user import AccountScheme
from src.schemas.user import CheckUsernameAvailabilitySchema
from src.schemas.user import ExistsResponseSchema
from src.schemas.user import UserInputSchema
from src.schemas.user import UserOutputSchema
from src.schemas.user import UserUpdateSchema
from src.services.user_service import UserService
from src.utils.auth import UserCredentials
from src.utils.auth import get_current_user_credentials
from src.utils.auth import validate_jwt_token
from src.utils.pydantic_utils import Username
from src.utils.stub import DependencyStub


router = APIRouter(
    prefix="/users", tags=["users"], dependencies=[Depends(validate_jwt_token)]
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
    user = await user_service.create_user(**user.model_dump())
    return UserOutputSchema.model_validate(user)


@router.post("/availability", response_model=ExistsResponseSchema)
async def check_if_username_is_available(
    payload: Annotated[CheckUsernameAvailabilitySchema, Body(...)],
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    return {
        "exists": await user_service.does_user_exists_caseinsensetive(payload.username)
    }


@router.post(
    "/{user_id}",
    status_code=HTTP_204_NO_CONTENT,
    summary="Update a user",
    description="Update user",
    response_description="User updated",
)
async def update_user(
    user_id: PydanticObjectId,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
    bio: Annotated[str, Form()] = None,
    image: Annotated[UploadFile, File()] = None,
    username: Username = Form(None),
):
    # TODO: maybe write a custom thing that would allow to validate form data through a pydantic model altogether
    await user_service.update_user(
        user_id, UserUpdateSchema(username=username, bio=bio, image=image)
    )


@router.get(
    "/",
    status_code=200,
    summary="Get user",
    description="Get user",
    response_description="User retrieved",
)
async def get_user_by_filters(
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
    return UserOutputSchema.model_validate(user)


@router.get("/me", status_code=200, summary="Get current user")
async def get_current_user(
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
) -> UserOutputSchema:
    user = await user_service.get_user_by_email(user_credentials.email)

    if user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    return UserOutputSchema.model_validate(user)


@router.delete(
    "/{user_id}",
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


@router.post("/account/link", status_code=200, summary="Link account")
async def link_account(
    account: AccountScheme,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    await user_service.link_account(account.user_id, account)
    return Response(status_code=200)


@router.post(
    "/account/unlink/{provider_name}/{provider_id}",
    status_code=200,
    summary="Link account",
)
async def unlink_account(
    provider_name: str,
    provider_id: str,
    user_service: Annotated[UserService, Depends(DependencyStub("user_service"))],
):
    await user_service.unlink_account(provider_id, provider_name)
    return Response(status_code=200)
