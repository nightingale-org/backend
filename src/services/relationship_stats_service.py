from __future__ import annotations

import contextlib

from beanie import PydanticObjectId
from beanie.odm.operators.update.general import Set
from pymongo.errors import DuplicateKeyError

from src.db.models.relationship import RelationshipStats
from src.db.models.relationship import RelationshipType
from src.services.base_service import BaseService


class RelationshipStatsService(BaseService):
    async def reset_relationship_stats(
        self, user_id: PydanticObjectId, relationship_type: RelationshipType
    ) -> None:
        with contextlib.suppress(
            DuplicateKeyError
        ):  # TODO: figure out why this happens and maybe change the request
            await RelationshipStats.find_one(
                RelationshipStats.user_id == user_id,
                RelationshipStats.relationship_type == relationship_type,
            ).upsert(
                Set({RelationshipStats.unseen_count: 0}),
                on_insert=RelationshipStats(
                    user_id=user_id, relationship_type=relationship_type
                ),
            )
