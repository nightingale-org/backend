from __future__ import annotations

from beanie import Document
from beanie import Link
from beanie import PydanticObjectId
from pydantic import AwareDatetime
from pydantic import Field
from pymongo import IndexModel
from pymongo.collation import Collation
from pymongo.collation import CollationStrength

from src.utils.datetime_utils import current_timeaware_utc
from src.utils.pydantic_utils import Username


class User(Document):
    username: Username | None = None
    image: str | None = None
    bio: str | None = None
    email: str
    email_verified_at: AwareDatetime | None = Field(alias="emailVerified")
    created_at: AwareDatetime | None = Field(default_factory=current_timeaware_utc)

    class Settings:
        name = "users"
        use_state_management = True
        indexes = [
            IndexModel(
                "username",
                unique=True,
                collation=Collation(locale="en", strength=CollationStrength.SECONDARY),
            ),
        ]


class Account(Document):
    user_id: PydanticObjectId
    provider_name: str
    provider_account_id: str
    created_at: AwareDatetime | None = Field(default_factory=current_timeaware_utc)
    user: Link[User]

    class Settings:
        name = "accounts"
        use_state_management = True
