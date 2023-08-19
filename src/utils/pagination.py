from __future__ import annotations

import base64
import datetime

from typing import Any
from typing import Generic
from typing import TypeVar

from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from starlette.status import HTTP_400_BAD_REQUEST


T = TypeVar("T", bound=type[BaseModel])


def pagination(
    payload_pydantic_model: T, expected_entity_name: str, **next_cursor_kwargs: Any
):
    def wrapper(next_cursor: str = Query(**next_cursor_kwargs)) -> T:
        try:
            decoded_cursor = decode_pagination_cursor(
                next_cursor, payload_pydantic_model
            )
        except (ValueError, OverflowError, MemoryError) as e:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail="Invalid pagination cursor"
            ) from e
        except (
            TypeError
        ):  # means it probably default to None and base64 complains about it
            try:
                return next_cursor_kwargs["default"]
            except KeyError:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, detail="Invalid pagination cursor"
                ) from None

        if decoded_cursor.entity_name != expected_entity_name:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Pagination cursor should be used for the {decoded_cursor.entity_name} entity instead",
            ) from None

        return decoded_cursor.payload

    return wrapper


class Cursor(BaseModel, Generic[T]):
    entity_name: str
    payload: T


def json_decoder_fallback(o: Any) -> Any:
    if isinstance(o, datetime.date | datetime.datetime):
        return o.isoformat()


def encode_pagination_cursor(entity_name: str, **data: Any) -> str:
    cursor_key_value_pairs = ",".join(
        f"{key}|{value}" for key, value in data.items() if value
    )
    return base64.b64encode(f"{entity_name}:{cursor_key_value_pairs}".encode()).decode(
        "utf-8"
    )


def decode_pagination_cursor(
    encoded_cursor: str, payload_pydantic_model: T
) -> Cursor[T]:
    decoded_str = base64.b64decode(encoded_cursor).decode("utf-8")

    entity_name, _, payload = decoded_str.partition(":")

    if not entity_name:
        raise ValueError("Invalid cursor: entity name is missing")

    if not payload:
        raise ValueError("Invalid cursor: payload is missing")

    key_value_pairs = payload.split(",")
    if key_value_pairs[0] == "":
        raise ValueError("Invalid cursor: payload is invalid")

    return Cursor[payload_pydantic_model].model_validate(
        {
            "entity_name": entity_name,
            "payload": dict(
                [tuple(key_value_pair.split("|")) for key_value_pair in key_value_pairs]
            ),
        }
    )
