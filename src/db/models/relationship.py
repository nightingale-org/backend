from __future__ import annotations

import enum

from typing import TYPE_CHECKING

import pymongo

from beanie import Document
from beanie import Link
from beanie import PydanticObjectId
from pymongo import IndexModel


if TYPE_CHECKING:
    from src.db.models import User


class RelationshipType(enum.IntEnum):
    pending = enum.auto()
    blocked = enum.auto()
    settled = enum.auto()


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
