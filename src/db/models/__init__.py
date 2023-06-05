from __future__ import annotations

from beanie import Document

from src.db.models.conversation import Conversation, Message
from src.db.models.relationship import Relationship
from src.db.models.user import Account, User


def gather_documents() -> list[type[Document]]:
    Relationship.update_forward_refs(User=User)
    Conversation.update_forward_refs(User=User)
    Message.update_forward_refs(User=User)

    return [Account, Relationship, User, Conversation, Message]


__all__ = ["User", "Relationship", "Account", "gather_documents"]
