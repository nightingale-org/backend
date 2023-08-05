from __future__ import annotations

from beanie import WriteRules

from src.db.models import Conversation
from src.db.models import Message
from src.db.models import User
from src.exceptions import BusinessLogicError
from src.services.base_service import BaseService


class MessageService(BaseService):
    async def save_message(self, conversation_id: str, text: str, sender_id: str):
        conversation = await Conversation.get(
            conversation_id, session=self._current_session
        )
        sender = await User.get(sender_id, session=self._current_session)

        if not sender:
            raise BusinessLogicError("Sender not found.", "sender_not_found")

        conversation.messages.append(
            Message(text=text, author=await User.get(sender_id))
        )
        await conversation.save(
            link_rule=WriteRules.WRITE, session=self._current_session
        )
