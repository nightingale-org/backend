from __future__ import annotations

from datetime import datetime

from beanie import Document
from beanie import Link
from beanie import PydanticObjectId
from pydantic import Field
from pymongo import IndexModel
from pymongo.collation import Collation
from pymongo.collation import CollationStrength


class User(Document):
    username: str | None = None
    image: str | None = None
    bio: str | None = None
    email: str
    email_verified_at: datetime | None = Field(alias="emailVerified")
    created_at: datetime | None = Field(default_factory=datetime.utcnow)

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
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    user: Link[User]

    class Settings:
        name = "accounts"
        use_state_management = True
