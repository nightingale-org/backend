from __future__ import annotations

import enum

from typing import TYPE_CHECKING

import pymongo

from beanie import Document
from beanie import Link
from beanie import PydanticObjectId
from pydantic import PositiveInt
from pymongo import IndexModel


if TYPE_CHECKING:
    from src.db.models import User


class RelationshipType(enum.IntEnum):
    pending = enum.auto()
    blocked = enum.auto()
    settled = enum.auto()


class RelationshipStats(Document):
    user_id: PydanticObjectId
    relationship_type: RelationshipType
    unseen_count: PositiveInt = 0

    class Settings:
        name = "relationship_notification_stats"
        use_state_management = True
        indexes = [
            IndexModel(
                [
                    ("user_id", pymongo.ASCENDING),
                    ("relationship_type", pymongo.ASCENDING),
                ],
                unique=True,
            ),
        ]


class Relationship(Document):
    target: Link[User]
    type: RelationshipType
    initiator_user_id: PydanticObjectId

    class Settings:
        indexes = [
            IndexModel(
                [
                    ("target.$id", pymongo.ASCENDING),
                    ("initiator_user_id", pymongo.ASCENDING),
                ],
                unique=True,
            ),
        ]
        name = "relationships"
