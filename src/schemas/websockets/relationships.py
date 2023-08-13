from __future__ import annotations

from beanie import PydanticObjectId
from pydantic import BaseModel

from src.db.models.relationship import RelationshipType


class RelationshipEventsSeenPayload(BaseModel):
    type: RelationshipType


class RelationshipDeletePayload(BaseModel):
    type: RelationshipType
    relationship_id: PydanticObjectId
