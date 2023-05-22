from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from beanie import BackLink, Document, Indexed, Link, PydanticObjectId
from pydantic import EmailStr, Field
from pymongo import TEXT, IndexModel


class User(Document):
    name: Optional[Indexed(str, unique=True)] = None
    email: Optional[Indexed(EmailStr, unique=True)] = None
    email_verified_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    image: Optional[str] = None
    accounts: BackLink[List[Account]] = Field(original_field="user_id")

    class Settings:
        name = "users"
        use_state_management = True


class Account(Document):
    user_id: PydanticObjectId
    provider_name: str
    provider_account_id: str
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    access_token_expires: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    # TODO update on update
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    expires_at: Optional[int] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
    session_state: Optional[str] = None
    user: Link[User]

    class Settings:
        name = "accounts"
        indexes = [
            IndexModel(
                [("provider_id", TEXT), ("provider_account_id", TEXT)], unique=True
            )
        ]
        use_state_management = True


User.update_forward_refs()
