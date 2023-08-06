from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated

from beanie import BackLink
from beanie import Document
from beanie import Link
from pydantic import AwareDatetime
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from pydantic_core.core_schema import FieldValidationInfo

from src.utils.datetime_utils import current_timeaware_utc


if TYPE_CHECKING:
    from src.db.models import User


class Message(Document):
    text: str
    created_at: AwareDatetime = Field(default_factory=current_timeaware_utc)

    seen_by: list[Link[User]] = Field(default_factory=list)
    conversation: BackLink[Conversation] = Field(original_field="messages")
    author: User

    class Settings:
        name = "messages"

    # TODO: add attachments


class Conversation(Document):
    created_at: AwareDatetime = Field(default_factory=current_timeaware_utc)
    last_message_at: AwareDatetime | None = Field(default_factory=current_timeaware_utc)
    name: str | None = None
    is_group: bool
    user_limit: Annotated[int, Field(ge=2, strict=True)] | None = None

    @model_validator(mode="after")
    def validate_members(self):
        if not self.is_group:
            # is_group field is not set, so we can't validate members. It will raise a ValidationError later anyway.
            return self

        members = self.members
        if len(members) > 2 and not self.is_group:
            raise ValueError("is_group must be True for group conversations.")

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
    members: list[Link[User]] = Field(default_factory=list)

    class Settings:
        name = "conversations"
