from __future__ import annotations

from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel

from src.services.base_service import PaginatedResult
from src.utils.pagination import encode_pagination_cursor


T = TypeVar("T", bound=BaseModel)


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    has_more: bool
    next_cursor: str | None = None

    @classmethod
    def from_paginated_result(
        cls, result: PaginatedResult[Any]
    ) -> PaginatedResponse[T]:
        if not result.has_more:
            return cls(data=result.data, has_more=False)

        cursor_metadata = result.next_cursor_metadata

        return cls(
            data=result.data,
            has_more=True,
            next_cursor=encode_pagination_cursor(
                cursor_metadata.entity_name, **cursor_metadata.cursor_values
            ),
        )
