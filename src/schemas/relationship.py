from __future__ import annotations

import enum

from typing import Literal

from beanie import PydanticObjectId
from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from src.db.models import User
from src.db.models.relationship import RelationshipType
from src.utils.datetime_utils import current_timeaware_utc_datetime


class RelationshipTypeExpanded(enum.IntEnum):
    ingoing_request = enum.auto()
    outgoing_request = enum.auto()
    blocked = enum.auto()
    settled = enum.auto()


class RelationshipListItemSchema(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    target: User
    type: RelationshipTypeExpanded
    created_at: AwareDatetime = Field(default_factory=current_timeaware_utc_datetime)

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(
        cls,
        v: Literal["ingoing"]
        | Literal["outgoing"]
        | RelationshipType
        | RelationshipTypeExpanded,
    ):
        if isinstance(v, RelationshipTypeExpanded):
            return v

        if v == "ingoing":
            return RelationshipTypeExpanded.ingoing_request
        elif v == "outgoing":
            return RelationshipTypeExpanded.outgoing_request
        elif v == RelationshipType.settled:
            return RelationshipTypeExpanded.settled
        elif v == RelationshipType.blocked:
            return RelationshipTypeExpanded.blocked

        raise ValueError(f"Invalid relationship type {v}")


class FriendRequestPayload(BaseModel):
    username: str


class BlockUserSchema(BaseModel):
    user_id: str


class UpdateRelationshipStatusPayload(BaseModel):
    new_state: Literal["accepted", "ignored"]
    relationship_id: PydanticObjectId
