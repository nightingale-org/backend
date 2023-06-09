from __future__ import annotations

from beanie import PydanticObjectId
from pydantic import BaseModel
from pydantic import conlist


class CreateConversationSchema(BaseModel):
    is_group: bool
    members: conlist(PydanticObjectId, min_items=2)
    name: str | None = None
    user_limit: int | None = None
