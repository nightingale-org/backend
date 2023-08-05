from __future__ import annotations

import enum

from typing import TYPE_CHECKING

import pymongo

from beanie import Document
from beanie import PydanticObjectId
from pymongo import IndexModel


if TYPE_CHECKING:
    from src.db.models import User


@enum.unique
class RelationshipTypeFlags(enum.IntFlag):
    ingoing_request = enum.auto()
    outgoing_request = enum.auto()
    blocked = enum.auto()
    established = enum.auto()


class Relationship(Document):
    target: User
    type: RelationshipTypeFlags
    initiator_user_id: PydanticObjectId

    class Settings:
        indexes = [
            IndexModel(
                [
                    ("user._id", pymongo.ASCENDING),
                    ("initiator_user_id", pymongo.ASCENDING),
                ],
                unique=True,
            ),
        ]
        name = "relationships"
