from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from beanie.odm.operators.update.general import Set
from pymongo.errors import DuplicateKeyError

from src.db.models import User
from src.db.models.relationship import Relationship
from src.db.models.relationship import RelationshipType
from src.exceptions import BusinessLogicError
from src.services.base_service import BaseService
from src.utils.orm_utils import get_collection_name_from_model


class RelationshipService(BaseService):
    async def get_relationships(
        self,
        relationship_type: RelationshipType,
        email: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if relationship_type == RelationshipType.blocked:
            match_item = {"initiator.email": email}
        else:
            match_item = {"$or": [{"target.email": email}, {"initiator.email": email}]}

        expand_type_step: dict[str, Any] = {}
        if relationship_type == RelationshipType.pending:
            expand_type_step = {
                "type": {
                    "$cond": {
                        "if": {"$eq": ["$initiator.email", email]},
                        "then": "outgoing",
                        "else": "ingoing",
                    }
                },
            }

        return (
            await Relationship.find(Relationship.type == relationship_type)
            .aggregate(
                [
                    {
                        "$lookup": {
                            "from": get_collection_name_from_model(User),
                            "localField": "initiator_user_id",
                            "foreignField": "_id",
                            "as": "initiator",
                        },
                    },
                    {
                        "$lookup": {
                            "from": get_collection_name_from_model(User),
                            "localField": "target.$id",
                            "foreignField": "_id",
                            "as": "target",
                        }
                    },
                    {
                        "$match": match_item,
                    },
                    {
                        "$unwind": "$initiator",
                    },
                    {
                        "$unwind": "$target",
                    },
                    {
                        "$set": {
                            **expand_type_step,
                            "target": {
                                "$cond": {
                                    "if": {
                                        "$eq": ["$initiator.email", email],
                                    },
                                    "then": "$target",
                                    "else": "$initiator",
                                }
                            },
                        }
                    },
                    {
                        "$limit": limit,
                    },
                    {
                        "$project": {
                            "target": 1,
                            "type": 1,
                        }
                    },
                ],
                session=self._current_session,
            )
            .to_list()
        )

    async def establish_relationship(self, username: str, *, initiator_email: str):
        target_user = await User.find_one(
            User.username == username, session=self._current_session
        )
        if not target_user:
            raise BusinessLogicError(
                "Oh no, it looks like I couldn't find the person you were searching for.",
                "user_not_found",
            )

        initiator = await User.find_one(
            User.email == initiator_email, session=self._current_session
        )
        if initiator.id == target_user.id:
            raise BusinessLogicError(
                "You can't send a friend request to yourself", "self_reference_error"
            )

        friend_request_from_relationship_partner_was_made = await Relationship.find_one(
            {
                "initiator_user_id": target_user.id,
                "type": RelationshipType.pending,
                "target._id": initiator.id,
            }
        )

        if friend_request_from_relationship_partner_was_made:
            raise BusinessLogicError(
                "You already have a pending friend request from this user.",
                "already_received_friend_request",
            )

        try:
            await Relationship(
                initiator_user_id=initiator.id,
                target=target_user,
                type=RelationshipType.pending,
            ).create(session=self._current_session)
        except DuplicateKeyError as ex:
            raise BusinessLogicError(
                "You already have a pending request to this user.",
                "already_send_request",
            ) from ex

    async def block_user(self, *, initiator_user_id: str, partner_user_id: str) -> None:
        await Relationship.find_one(
            Relationship.partner.id == PydanticObjectId(partner_user_id),
            Relationship.initiator.email == initiator_user_id,
            fetch_links=True,
            session=self._current_session,
        ).update_one(
            Set({Relationship.type: RelationshipType.blocked}),
            session=self._current_session,
        )
