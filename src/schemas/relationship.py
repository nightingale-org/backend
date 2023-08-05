from __future__ import annotations

from beanie import PydanticObjectId
from pydantic import BaseModel

from src.db.models import User
from src.db.models.relationship import RelationshipTypeFlags


class RelationshipSchema(BaseModel):
    user: User
    type: RelationshipTypeFlags
    initiator_user_id: PydanticObjectId


class CreateRelationshipInputSchema(BaseModel):
    username: str


class BlockUserSchema(BaseModel):
    user_id: str
