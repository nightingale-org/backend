from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import enum

from fastapi import Query
from pydantic import create_model


def int_enum_query(
    alias: str, enum_class: type[enum.IntEnum] | type[enum.IntFlag], **query_kwargs
):
    """
    If you annotate a Query with IntEnum/IntFlag, FastAPI won't be able to parse it.
    This helper solves this problem by parsing the query as an integer and then validating it as IntEnum/IntFlag.
    """
    pydantic_model = create_model("Model", enum=(enum_class, ...))

    # Don't use Annotated here, It will break the code since FastAPI wouldn't be able to resolve
    # alias and query_kwargs from the outer scope
    def inner(
        q: int = Query(
            alias=alias,
            **query_kwargs,
        )
    ):
        # Validation error will be handled by FastAPI
        return pydantic_model(enum=q).enum

    return inner
