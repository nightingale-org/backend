from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from beanie import BackLink, Document, Link
from pydantic import Field, conint, validator

if TYPE_CHECKING:
    from src.db.models import User


class Message(Document):
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    seen_by: list[Link[User]]
    conversation: BackLink[Conversation] = Field(original_field="messages")
    author: Link[User]

    # TODO: add attachments


class Conversation(Document):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime | None = Field(default_factory=datetime.utcnow)
    name: str | None = None
    is_group: bool
    user_limit: conint(ge=2, strict=True) | None = None

    @validator("user_limit")
    def validate_user_limit(cls, v, values):
        if not values.get("is_group") and v:
            raise ValueError("user_limit can only be set for group conversations.")
        return v

    @validator("name")
    def validate_name(cls, v, values):
        if not values.get("is_group") and v:
            raise ValueError("name can only be set for group conversations.")
        return v

    messages: Link[list[Message]]
    users: Link[list[User]]
