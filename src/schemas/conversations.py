from __future__ import annotations

from pydantic import BaseModel

from src.db.models import User


class CreateConversationSchema(BaseModel):
    is_group: bool
    members: list[User]
    name: str | None = None
    user_limit: int | None = None
