from __future__ import annotations

from typing import Generic
from typing import TypeVar

from pydantic import BaseModel


DataT = TypeVar("DataT", bound=BaseModel)


class WebsocketEvent(BaseModel, Generic[DataT]):
    event_name: str
    data: DataT


class NewConversationEvent(BaseModel):
    pass
