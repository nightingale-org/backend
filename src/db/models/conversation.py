from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated

import pymongo

from beanie import BackLink
from beanie import Document
from beanie import Link
from pydantic import AwareDatetime
from pydantic import Field
from pydantic import HttpUrl
from pydantic import field_validator
from pydantic import model_validator
from pydantic_core.core_schema import FieldValidationInfo
from pymongo import IndexModel

from src.utils.datetime_utils import current_timeaware_utc_datetime


if TYPE_CHECKING:
    from src.db.models import User


class Message(Document):
    text: str
    created_at: AwareDatetime = Field(default_factory=current_timeaware_utc_datetime)

    seen_by: list[Link[User]] = Field(default_factory=list)
    conversation: BackLink[Conversation] = Field(original_field="messages")
    author: User

    class Settings:
        name = "messages"
        indexes = [
            IndexModel([("created_at", pymongo.DESCENDING)]),
            IndexModel([("text", pymongo.TEXT)]),
        ]

    # TODO: add attachments


class Conversation(Document):
    created_at: AwareDatetime = Field(default_factory=current_timeaware_utc_datetime)
    name: str | None = None
    user_limit: Annotated[int, Field(ge=2, strict=True)] | None = None
    is_group: bool
    avatar_url: HttpUrl | None = None

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v, info: FieldValidationInfo):
        if not info.data.get("is_group") and v:
            raise ValueError("avatar_url can only be set for group conversations.")
        return v

    @model_validator(mode="after")
    def validate_members(self):
        members = self.members

        if not self.is_group and len(members) > 2:
            raise ValueError("One-to-one conversation can only have 2 members.")

        if len(members) <= 1:
            raise ValueError(
                "Conversation has to have at least 2 members. It can be either a group or a one-to-one conversation."
            )

        return self

    @field_validator("user_limit")
    @classmethod
    def validate_user_limit(cls, v, info: FieldValidationInfo):
        if not info.data.get("is_group") and v:
            raise ValueError("user_limit can only be set for group conversations.")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v, info: FieldValidationInfo):
        if not info.data.get("is_group") and v:
            raise ValueError("name can only be set for group conversations.")
        return v

    messages: list[Link[Message]] = Field(default_factory=list)
    members: list[Link[User]]

    class Settings:
        name = "conversations"
        indexes = [
            IndexModel([("created_at", pymongo.DESCENDING)]),
        ]
