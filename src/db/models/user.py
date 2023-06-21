from __future__ import annotations

from datetime import datetime

from beanie import Document
from beanie import Indexed
from beanie import Link
from beanie import PydanticObjectId
from pydantic import Field

from src.utils.pydantic_utils import Username


class User(Document):
    username: Indexed(Username, unique=True) | None = None
    image: str | None = None
    bio: str | None = None
    email: str
    email_verified_at: datetime | None = Field(alias="emailVerified")
    created_at: datetime | None = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        use_state_management = True


class Account(Document):
    user_id: PydanticObjectId
    provider_name: str
    provider_account_id: str
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    user: Link[User]

    class Settings:
        name = "accounts"
        use_state_management = True
