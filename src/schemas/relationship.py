from __future__ import annotations

import enum

from typing import Literal

from beanie import PydanticObjectId
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from src.db.models import User
from src.db.models.relationship import RelationshipType


class RelationshipTypeExpanded(enum.IntEnum):
    ingoing_request = enum.auto()
    outgoing_request = enum.auto()
    blocked = enum.auto()
    settled = enum.auto()


class RelationshipListItemSchema(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    target: User
    type: RelationshipTypeExpanded

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(
        cls, v: Literal["ingoing"] | Literal["outgoing"] | RelationshipType
    ):
        if v == "ingoing":
            return RelationshipTypeExpanded.ingoing_request
        elif v == "outgoing":
            return RelationshipTypeExpanded.outgoing_request
        elif v == RelationshipType.settled:
            return RelationshipTypeExpanded.settled
        elif v == RelationshipType.blocked:
            return RelationshipTypeExpanded.blocked

        raise ValueError(f"Invalid relationship type {v}")


class CreateRelationshipInputSchema(BaseModel):
    username: str


class BlockUserSchema(BaseModel):
    user_id: str
