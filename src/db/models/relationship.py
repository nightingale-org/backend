from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

from beanie import Document
from beanie import PydanticObjectId
from pymongo import TEXT
from pymongo import IndexModel


if TYPE_CHECKING:
    from src.db.models import User


class RelationshipType(IntEnum):
    ingoing_request = 1
    outgoing_request = 2
    blocked = 3
    established = 4


class Relationship(Document):
    with_user: User
    type: RelationshipType
    initiator_id: PydanticObjectId

    class Settings:
        indexes = [
            "type",
            IndexModel([("with_user._id", TEXT), ("initiator_id", TEXT)], unique=True),
        ]
        name = "relationships"
