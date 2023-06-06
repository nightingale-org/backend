from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from beanie import BackLink
from beanie import Document
from beanie import Link
from pydantic import Field
from pydantic import conint
from pydantic import root_validator
from pydantic import validator


if TYPE_CHECKING:
    from src.db.models import User


class Message(Document):
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    seen_by: list[Link[User]] = Field(default_factory=list)
    conversation: BackLink[Conversation] = Field(original_field="messages")
    author: User

    class Settings:
        name = "messages"

    # TODO: add attachments


class Conversation(Document):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime | None = Field(default_factory=datetime.utcnow)
    name: str | None = None
    is_group: bool
    user_limit: conint(ge=2, strict=True) | None = None

    @root_validator
    def validate_members(cls, values):
        if not (is_group := values.get("is_group")) and not isinstance(
            values.get("is_group"), bool
        ):
            # is_group field is not set, so we can't validate members. It will raise a ValidationError later anyway.
            return values

        members = values["members"]
        if len(members) > 2 and not is_group:
            raise ValueError("is_group must be True for group conversations.")

        if len(members) <= 1:
            raise ValueError(
                "Conversation has to have at least 2 members. It can be either a group or a one-to-one conversation."
            )

        return values

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

    messages: list[Link[Message]] = Field(default_factory=list)
    members: list[Link[User]] = Field(default_factory=list)

    class Settings:
        name = "conversations"
