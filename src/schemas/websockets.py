from __future__ import annotations

from typing import Generic
from typing import TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel


DataT = TypeVar("DataT", bound=BaseModel)


class WebsocketEvent(GenericModel, Generic[DataT]):
    event_name: str
    data: DataT


class NewConversationEvent(BaseModel):
    pass
