from __future__ import annotations

from beanie import PydanticObjectId

from src.db.models import Conversation
from src.db.models import User
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
        self,
        is_group: bool,
        members: list[User],
        name: str | None = None,
        user_limit: int | None = None,
    ) -> Conversation:
        conversation = Conversation(
            name=name, is_group=is_group, members=members, user_limit=user_limit
        )
        await conversation.save(session=self._current_session)
        return conversation

    async def get_conversation(
        self, conversation_id: str | PydanticObjectId
    ) -> Conversation:
        return await Conversation.get(
            conversation_id, fetch_links=True, session=self._current_session
        )
