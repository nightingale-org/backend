from __future__ import annotations

from typing import Any

import pymongo

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In

from src.db.models import Conversation
from src.db.models import User
from src.schemas.conversations import ConversationPreviewSchemaCursorPayload
from src.schemas.conversations import CreateConversationSchema
from src.services.base_service import BaseService
from src.services.base_service import CursorMetadata
from src.services.base_service import PaginatedResult
from src.utils.orm_utils import get_collection_name_from_model


class ConversationService(BaseService):
    async def get_conversation_previews(
        self,
        email: str,
        limit: int = 30,
        cursor_payload: ConversationPreviewSchemaCursorPayload | None = None,
    ) -> PaginatedResult[dict[str, Any]]:
        user: User = await User.find_one(
            User.email == email, session=self._current_session
        )
        limit_plus_one_entry_to_check_if_has_more = limit + 1

        extra_aggregation_steps: list[dict[str, Any]] = []

        if (
            cursor_payload
            and cursor_payload.last_created_at
            and cursor_payload.last_message_created_at
        ):
            extra_aggregation_steps.append(
                {
                    "$match": {
                        "$or": [
                            {
                                "last_message.created_at": {
                                    "$lt": cursor_payload.last_message_created_at
                                }
                            },
                            {
                                "$and": [
                                    {"last_message.created_at": {"$eq": "created_at"}},
                                    {
                                        "created_at": {
                                            "$lt": cursor_payload.last_created_at
                                        }
                                    },
                                ]
                            },
                        ]
                    }
                }
            )
        elif cursor_payload and cursor_payload.last_created_at:
            extra_aggregation_steps.append(
                {"$match": {"created_at": {"$lt": cursor_payload.last_created_at}}}
            )

        result = await Conversation.aggregate(
            [
                {
                    "$lookup": {
                        "from": get_collection_name_from_model(User),
                        "localField": "members.$id",
                        "foreignField": "_id",
                        "as": "members",
                    }
                },
                {"$match": {"members._id": user.id}},
                {
                    "$project": {
                        "created_at": 1,
                        "name": {
                            "$cond": {
                                "if": {"$eq": ["$is_group", False]},
                                "then": {
                                    "$cond": {
                                        "if": {
                                            "$eq": [
                                                {"$arrayElemAt": ["$members._id", 0]},
                                                user.id,
                                            ],
                                        },
                                        "then": {
                                            "$arrayElemAt": ["$members.username", 1]
                                        },
                                        "else": {
                                            "$arrayElemAt": ["$members.username", 0]
                                        },
                                    }
                                },
                                "else": "$name",
                            }
                        },
                        "user_limit": 1,
                        "last_message": {
                            "$ifNull": [{"$arrayElemAt": ["$messages", -1]}, None]
                        },
                        "last_message_seen": {
                            "$cond": {
                                "if": {
                                    "$eq": ["$last_message", None],
                                },
                                "then": True,
                                "else": {
                                    "$cond": {
                                        "if": {
                                            "$in": [
                                                user.id,
                                                {
                                                    "$ifNull": [
                                                        "$last_message.seen_by.$id",
                                                        [],
                                                    ]
                                                },
                                            ],
                                        },
                                        "then": True,
                                        "else": False,
                                    }
                                },
                            }
                        },
                        "is_group": 1,
                        "avatar_url": {
                            "$cond": {
                                "if": {"$eq": ["$is_group", False]},
                                "then": {
                                    "$cond": {
                                        "if": {
                                            "$eq": [
                                                {"$arrayElemAt": ["$members._id", 0]},
                                                user.id,
                                            ],
                                        },
                                        "then": {"$arrayElemAt": ["$members.image", 1]},
                                        "else": {"$arrayElemAt": ["$members.image", 0]},
                                    }
                                },
                                "else": "$avatar_url",
                            }
                        },
                    }
                },
                *extra_aggregation_steps,
                {
                    "$sort": {
                        "last_message.created_at": pymongo.DESCENDING,
                        "created_at": pymongo.DESCENDING,
                    }
                },
                {"$limit": limit_plus_one_entry_to_check_if_has_more},
            ],
            session=self._current_session,
        ).to_list(length=limit_plus_one_entry_to_check_if_has_more)

        if len(result) == limit_plus_one_entry_to_check_if_has_more:
            result = result[:limit]

            try:
                last_message_created_at = result[-1]["last_message"]
            except KeyError:
                last_message_created_at = None

            return PaginatedResult(
                result,
                has_more=True,
                next_cursor_metadata=CursorMetadata(
                    entity_name="conversation",
                    cursor_values={
                        "last_created_at": result[-1]["created_at"],
                        "last_message_created_at": last_message_created_at,
                    },
                ),
            )

        return PaginatedResult(result, has_more=False)

    async def create_conversation(
        self, create_input: CreateConversationSchema
    ) -> Conversation:
        members = await User.find(
            In(User.id, create_input.members), session=self._current_session
        ).to_list()

        if len(members) != len(create_input.members):
            raise ValueError("Invalid member ids")

        conversations = await Conversation.aggregate(
            [
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "members.$id",
                        "foreignField": "_id",
                        "as": "members",
                    }
                },
                {
                    "$match": {
                        "members": {
                            "$size": len(members),
                            "$elemMatch": {
                                "_id": {"$in": [member.id for member in members]}
                            },
                        }
                    }
                },
            ],
            session=self._current_session,
        ).to_list()

        if len(conversations) >= 2:
            raise ValueError("Internal error: multiple conversations found")
        elif len(conversations) == 1:
            raise ValueError("Conversation already exists")

        conversation = Conversation(
            name=create_input.name,
            is_group=create_input.is_group,
            members=members,
            user_limit=create_input.user_limit,
        )
        await conversation.create(session=self._current_session)
        return conversation

    async def get_conversation(
        self, conversation_id: str | PydanticObjectId
    ) -> Conversation:
        return await Conversation.get(
            conversation_id, fetch_links=True, session=self._current_session
        )
