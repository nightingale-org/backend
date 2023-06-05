from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

from beanie import BackLink, Document, Link
from pydantic import Field

if TYPE_CHECKING:
    from src.db.models import User


class RelationshipType(IntEnum):
    ingoing_request = 1
    outgoing_request = 2
    blocked = 3
    established = 4


class Relationship(Document):
    with_user: Link[User]
    type: RelationshipType

    initiator: BackLink[User] = Field(original_field="relationships")

    class Settings:
        indexes = ["type", "with_user.id"]
        name = "relationships"
