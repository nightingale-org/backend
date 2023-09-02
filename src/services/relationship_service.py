from __future__ import annotations

import asyncio

from typing import Any

from beanie import PydanticObjectId
from beanie.odm.operators.update.general import Set
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from src.db.models import Conversation
from src.db.models import User
from src.db.models.relationship import Relationship
from src.db.models.relationship import RelationshipType
from src.exceptions import BusinessLogicError
from src.schemas.relationship import RelationshipListItemSchema
from src.schemas.relationship import RelationshipTypeExpanded
from src.schemas.relationship import UpdateRelationshipStatusPayload
from src.schemas.websockets.relationships import RelationshipDeletePayload
from src.services.base_service import BaseService
from src.utils.orm_utils import get_collection_name_from_model
from src.utils.socketio.socket_manager import SocketIOManager


class RelationshipService(BaseService):
    def __init__(
        self, db_client: AsyncIOMotorClient, socketio_manager: SocketIOManager
    ):
        super().__init__(db_client)
        self._socketio_manager = socketio_manager

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

        user = await User.find_one(User.email == email, session=self._current_session)

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
                        "$lookup": {
                            "from": get_collection_name_from_model(Conversation),
                            "let": {"target_user_id": "$target._id"},
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {
                                            "$and": [
                                                {"$in": [user.id, "$members.$id"]},
                                                {
                                                    "$in": [
                                                        "$$target_user_id",
                                                        "$members.$id",
                                                    ]
                                                },
                                            ]
                                        }
                                    }
                                },
                                {"$project": {"_id": 1}},
                            ],
                            "as": "conversations",
                        }
                    },
                    {
                        "$limit": limit,
                    },
                    {
                        "$project": {
                            "target": 1,
                            "type": 1,
                            "created_at": 1,
                            "conversations": 1,
                            "conversation_id": {
                                "$cond": {
                                    "if": {"$eq": ["$type", RelationshipType.settled]},
                                    "then": {"$arrayElemAt": ["$conversations._id", 0]},
                                    "else": None,
                                }
                            },
                        }
                    },
                ],
                session=self._current_session,
            )
            .to_list()
        )

    async def create_friend_request(self, username: str, *, initiator_email: str):
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
            new_relationship = await Relationship(
                initiator_user_id=initiator.id,
                target=target_user,
                type=RelationshipType.pending,
            ).create(session=self._current_session)
        except DuplicateKeyError as ex:
            raise BusinessLogicError(
                "You already have a pending request to this user.",
                "already_send_request",
            ) from ex

        await asyncio.gather(
            *[
                self._socketio_manager.emit_to_user_by_email(
                    email=target_user.email,
                    event_name="relationship:new",
                    payload=RelationshipListItemSchema(
                        _id=new_relationship.id,
                        target=initiator,
                        type=RelationshipTypeExpanded.ingoing_request,
                    ),
                    raise_if_recipient_not_connected=False,
                ),
                self._socketio_manager.emit_to_user_by_email(
                    email=initiator_email,
                    event_name="relationship:new",
                    payload=RelationshipListItemSchema(
                        _id=new_relationship.id,
                        target=target_user,
                        type=RelationshipTypeExpanded.outgoing_request,
                    ),
                    raise_if_recipient_not_connected=False,
                ),
            ]
        )

        return new_relationship

    async def update_relationship_status(
        self,
        payload: UpdateRelationshipStatusPayload,
    ):
        # TODO: optimize these queries
        relationship = await Relationship.find_one(
            Relationship.id == payload.relationship_id,
            session=self._current_session,
            fetch_links=True,
        )
        initiator = await User.get(relationship.initiator_user_id)

        if payload.new_state == "accepted":
            async with self.transaction():
                await relationship.update(
                    Set({Relationship.type: RelationshipType.settled}),
                    session=self._current_session,
                )

                # TODO: move to a different service
                await Conversation(
                    members=[initiator, relationship.target],
                    is_group=False,
                ).create(session=self._current_session)

            # TODO: plus add relationship to all tab on the other's user side
            await self._socketio_manager.emit_to_user_by_email(
                initiator.email,
                "relationship:delete",
                RelationshipDeletePayload(
                    type=RelationshipType.pending, relationship_id=relationship.id
                ),
            )
            return

        await relationship.delete(session=self._current_session)
        await self._socketio_manager.emit_to_user_by_email(
            initiator.email,
            "relationship:request_rejected",
            payload={
                "relationship_id": str(relationship.id),
                "type": relationship.type,
            },
            raise_if_recipient_not_connected=False,
        )

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

    async def delete_friend(
        self, *, relationship_id: PydanticObjectId, user_email: str
    ) -> None:
        user = await User.find_one(
            User.email == user_email, session=self._current_session
        )
        if not user:
            raise BusinessLogicError(
                "You can't delete a relationship that you are not a part of.",
                "prohibited_operation",
            )

        relationship = await Relationship.aggregate(
            [
                {
                    "$match": {
                        "_id": relationship_id,
                    }
                },
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
                    "$unwind": "$initiator",
                },
                {
                    "$unwind": "$target",
                },
                {
                    "$lookup": {
                        "from": get_collection_name_from_model(Conversation),
                        "let": {"target_user_id": "$target._id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$in": [user.id, "$members.$id"]},
                                            {
                                                "$in": [
                                                    "$$target_user_id",
                                                    "$members.$id",
                                                ]
                                            },
                                        ]
                                    }
                                }
                            },
                            {"$project": {"_id": 1}},
                        ],
                        "as": "conversations",
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "conversation_id": {
                            "$cond": {
                                "if": {"$eq": ["$type", RelationshipType.settled]},
                                "then": {"$arrayElemAt": ["$conversations._id", 0]},
                                "else": None,
                            }
                        },
                    }
                },
            ]
        ).to_list()

        try:
            relationship = relationship[0]
        except IndexError:
            raise BusinessLogicError(
                "You can't delete a relationship that you are not a part of.",
                "prohibited_operation",
            ) from None

        async with self.transaction():
            await Relationship.find_one(
                Relationship.id == relationship_id,
            ).delete(session=self._current_session)

            await Conversation.find_one(
                Conversation.id == relationship["conversation_id"]
            ).delete(session=self._current_session)
