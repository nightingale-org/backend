from __future__ import annotations

from pydantic import BaseModel

from src.db.models import User
from src.db.models.relationship import RelationshipType


class RelationshipSchema(BaseModel):
    with_user: User
    type: RelationshipType


class CreateRelationshipInputSchema(BaseModel):
    username: str


class BlockUserSchema(BaseModel):
    user_id: str
