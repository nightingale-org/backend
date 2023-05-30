from __future__ import annotations

from typing import TYPE_CHECKING, Any

from beanie.odm.operators.update.general import Set
from bson import ObjectId

from src.db.models import Account, User
from src.utils.pydantic_utils import map_raw_data_to_pydantic_fields

if TYPE_CHECKING:
    from src.api.v1.schemas import AccountScheme


class UserService:
    async def create_user(self, **data: Any) -> User:
        return await User.create(User(**data))

    async def get_user_by_filters(self, **filters: Any) -> User | None:
        provider_account_id = filters.pop("provider_account_id", None)

        if provider_account_id:
            return await self.get_user_by_account(
                provider_account_id=provider_account_id
            )

        return await User.find_one(filters, fetch_links=True)

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await User.get(user_id, fetch_links=True)

    async def get_users_to_chat_with(self, email: str) -> list[User]:
        return await User.find(User.email != email, fetch_links=True).to_list()

    async def get_user_by_email(self, email: str) -> User | None:
        return await User.find_one({"email": email}, fetch_links=True)

    async def get_user_by_account(self, provider_account_id: str) -> User | None:
        account = await Account.find_one(
            {"provider_account_id": provider_account_id},
            fetch_links=True,
        )
        return account.user if account else None

    async def update_user(self, user_id: str, **data: Any) -> None:
        await User.find_one(User.id == ObjectId(user_id)).update(
            Set(map_raw_data_to_pydantic_fields(data, User))
        )

    async def delete_user(self, user_id: str) -> bool:
        delete_result = await User.find_one(User.id == ObjectId(user_id)).delete()
        return delete_result.deleted_count > 0

    async def link_account(self, user_id: str, account: AccountScheme):
        user = await User.get(user_id, fetch_links=False)
        if not user:
            # TODO: Implement custom exception
            raise Exception("User not found")

        await Account(**account.dict(), user=user).save()

    async def unlink_account(
        self, provider_account_id: str, provider_name: str
    ) -> None:
        await Account.find_one(
            {"provider_account_id": provider_account_id, "provider_name": provider_name}
        ).delete()

    # TODO: Implement create_verification_token, get_verification_token, delete_verification_token
