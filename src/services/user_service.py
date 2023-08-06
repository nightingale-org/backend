from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import aioboto3

from beanie import PydanticObjectId
from beanie.odm.operators.update.general import Set
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.collation import Collation
from pymongo.collation import CollationStrength

from src.db.models import Account
from src.db.models import User
from src.exceptions import BusinessLogicError
from src.services.base_service import BaseService
from src.utils.orm_utils import compare_id
from src.utils.pydantic_utils import map_raw_data_to_pydantic_fields
from src.utils.s3 import upload_file


if TYPE_CHECKING:
    from src.schemas.user import AccountScheme
    from src.schemas.user import UserUpdateSchema


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

    async def does_user_exists_caseinsensetive(self, username: str) -> bool:
        return (
            len(
                await User.find(
                    User.username == username,
                    session=self._current_session,
                    collation=Collation(
                        locale="en", strength=CollationStrength.SECONDARY
                    ),
                )
                .limit(1)
                .to_list()
            )
            > 0
        )

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await User.get(user_id, fetch_links=True, session=self._current_session)

    async def get_users_to_chat_with(self, email: str) -> list[User]:
        return await User.find(
            User.email != email, fetch_links=True, session=self._current_session
        ).to_list()

    async def get_user_by_email(self, email: str) -> User | None:
        return await User.find_one(
            {"email": email},
            fetch_links=True,
            session=self._current_session,
        )

    async def get_user_by_account(self, provider_account_id: str) -> User | None:
        account = await Account.find_one(
            {"provider_account_id": provider_account_id},
            fetch_links=True,
            session=self._current_session,
        )
        return account.user if account else None

    async def update_user(
        self,
        user_id: PydanticObjectId,
        user_update_schema: UserUpdateSchema,
    ) -> None:
        data: dict[str, Any] = user_update_schema.model_dump(exclude_none=True)

        if not data:
            raise BusinessLogicError("No data to update", "no_data_to_update")

        if image := data.pop("image", None):
            image_url = await upload_file(
                self._s3_client,
                image,
                return_public_url=True,
                cache_file=False,
                file_name_prefix=str(user_id),
            )
            data["image"] = image_url

        await User.find_one(User.id == user_id).update(
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
            raise BusinessLogicError("User not found", "user_not_found")

        await Account(**account.model_dump(), user=user).create()

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
