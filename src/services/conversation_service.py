from __future__ import annotations

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In

from src.db.models import Conversation
from src.db.models import User
from src.schemas.conversations import CreateConversationSchema
from src.services.base_service import BaseService


class ConversationService(BaseService):
    async def get_all_conversations(
        self, email: str, limit: int = 20, skip: int = 0
    ) -> list[Conversation]:
        return await Conversation.aggregate(
            [
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "members.$id",
                        "foreignField": "_id",
                        "as": "members",
                    }
                },
                {"$match": {"members.email": email}},
                {"$limit": limit},
                {"$skip": skip},
            ],
            projection_model=Conversation,
            session=self._current_session,
        ).to_list(limit)

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
