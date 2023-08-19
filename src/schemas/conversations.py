from __future__ import annotations

from typing import Annotated

from beanie import PydanticObjectId
from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import Field

from src.schemas.user import UserOutputSchema


class CreateConversationSchema(BaseModel):
    members: Annotated[list[PydanticObjectId], Field(min_length=2)]
    name: str | None = None
    user_limit: int | None = None


class MessagePreviewSchema(BaseModel):
    text: str
    created_at: AwareDatetime
    author: UserOutputSchema


class ConversationPreviewSchemaCursorPayload(BaseModel):
    last_created_at: AwareDatetime
    last_message_created_at: AwareDatetime | None = None


class ConversationPreviewSchema(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    created_at: AwareDatetime
    name: str | None = None
    user_limit: Annotated[int, Field(ge=2, strict=True)] | None = None
    is_group: bool
    last_message: MessagePreviewSchema | None = None
    last_message_seen: bool
    avatar_url: str | None = None
