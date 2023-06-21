from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import aioboto3

from beanie.odm.operators.update.general import Set
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorClient

from src.db.models import Account
from src.db.models import User
from src.exceptions import BusinessLogicError
from src.services.base_service import BaseService
from src.utils.orm_utils import compare_id
from src.utils.pydantic_utils import map_raw_data_to_pydantic_fields
from src.utils.s3 import upload_file


if TYPE_CHECKING:
    from src.schemas.user import AccountScheme


class UserService(BaseService):
    def __init__(self, db_client: AsyncIOMotorClient, boto3_session: aioboto3.Session):
        super().__init__(db_client)
        self._s3_client = boto3_session

    async def create_user(self, **data: Any) -> User:
        return await User(**data).create(session=self._current_session)

    async def get_user_by_filters(self, **filters: Any) -> User | None:
        provider_account_id = filters.pop("provider_account_id", None)

        if provider_account_id:
            return await self.get_user_by_account(
                provider_account_id=provider_account_id
            )

        return await User.find_one(
            filters, fetch_links=True, session=self._current_session
        )

    async def does_user_exists(self, username: str) -> bool:
        return await User.find_one(
            User.username == username, session=self._current_session
        ).exists()

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await User.get(user_id, fetch_links=True, session=self._current_session)

    async def get_users_to_chat_with(self, email: str) -> list[User]:
        return await User.find(
            User.email != email, fetch_links=True, session=self._current_session
        ).to_list()

    async def get_user_by_email(self, email: str) -> User | None:
        return await User.find_one(
            {"email": email}, fetch_links=True, session=self._current_session
        )

    async def get_user_by_account(self, provider_account_id: str) -> User | None:
        account = await Account.find_one(
            {"provider_account_id": provider_account_id},
            fetch_links=True,
            session=self._current_session,
        )
        return account.user if account else None

    async def update_user(
        self, user_id: str, username: str | None = None, image: UploadFile | None = None
    ) -> None:
        data: dict[str, Any] = {}
        if image:
            image_url = await upload_file(
                self._s3_client, image, return_public_url=True
            )
            data["image"] = image_url

        if username:
            data["username"] = username

        await User.find_one(compare_id(User.id, user_id)).update(
            Set(map_raw_data_to_pydantic_fields(data, User)),
            session=self._current_session,
        )

    async def delete_user(self, user_id: str) -> bool:
        delete_result = await User.find_one(
            compare_id(User.id, user_id), session=self._current_session
        ).delete()
        return delete_result.deleted_count > 0

    async def link_account(self, user_id: str, account: AccountScheme):
        user = await User.get(user_id, fetch_links=False, session=self._current_session)
        if not user:
            raise BusinessLogicError("User not found")

        await Account(**account.dict(), user=user).create()

    async def unlink_account(
        self, provider_account_id: str, provider_name: str
    ) -> None:
        await Account.find_one(
            {
                "provider_account_id": provider_account_id,
                "provider_name": provider_name,
            },
            session=self._current_session,
        ).delete()

    # TODO: Implement create_verification_token, get_verification_token, delete_verification_token
