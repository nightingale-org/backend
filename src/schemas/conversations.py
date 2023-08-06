from __future__ import annotations

from typing import Annotated

from beanie import PydanticObjectId
from pydantic import BaseModel
from pydantic import Field


class CreateConversationSchema(BaseModel):
    is_group: bool
    members: Annotated[list[PydanticObjectId], Field(min_length=2)]
    name: str | None = None
    user_limit: int | None = None
