from __future__ import annotations

import re
from typing import Any, Optional, TypeVar

import pydantic
from beanie import Document
from pydantic.fields import ModelField

_T = TypeVar("_T", bound=Any)

USERNAME_REGEXP = re.compile(r"^[a-z0-9_]+$", re.IGNORECASE)


def map_raw_data_to_pydantic_fields(
    data: dict[str, _T], document_type: type[Document]
) -> dict[ModelField, _T]:
    pydantic_field_to_value_mapping = {}
    for key in data:
        if key not in document_type.__fields__:
            # TODO write a more descriptive error message
            raise Exception("Invalid field")

        pydantic_field_to_value_mapping[getattr(document_type, key)] = data[key]

    return pydantic_field_to_value_mapping


class AllOptional(pydantic.main.ModelMetaclass):
    def __new__(cls, name, bases, namespaces, **kwargs):
        annotations = namespaces.get("__annotations__", {})
        for base in bases:
            annotations.update(base.__annotations__)
        for field in annotations:
            if not field.startswith("__"):
                annotations[field] = Optional[annotations[field]]
        namespaces["__annotations__"] = annotations
        return super().__new__(cls, name, bases, namespaces, **kwargs)


class Username(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema: dict[str, Any]) -> None:
        field_schema.update(
            pattern="^[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}$",
            examples=["gleb32222", "GLEF1X"],
            min_length=5,
        )

    @classmethod
    def validate(cls, v: str) -> Username:
        if not isinstance(v, str):
            raise TypeError("string required")

        if len(v) < 5:
            raise ValueError("username is too short")

        m = USERNAME_REGEXP.fullmatch(v.upper())
        if not m:
            raise ValueError("invalid username format")

        return cls(v)

    def __repr__(self) -> str:
        return f"Username({super().__repr__()})"
