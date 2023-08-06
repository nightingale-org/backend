from __future__ import annotations

from typing import Annotated
from typing import Any
from typing import TypeVar

from beanie import Document
from pydantic.fields import Field
from typing_extensions import TypeAliasType


_T = TypeVar("_T", bound=Any)

Username = TypeAliasType(
    "Username",
    Annotated[
        str,
        Field(
            pattern=r"^[a-zA-Z0-9_]+$",  # any alphanumeric characters or underscores
            examples=["gleb32222", "GLEF1X", "alex_32222"],
            min_length=5,
            title="Username",
        ),
    ],
)


def map_raw_data_to_pydantic_fields(
    data: dict[str, _T], document_type: type[Document]
) -> dict[Field, _T]:
    pydantic_field_to_value_mapping = {}
    for key in data:
        if key not in document_type.model_fields:
            # TODO write a more descriptive error message
            raise Exception("Invalid field")

        pydantic_field_to_value_mapping[getattr(document_type, key)] = data[key]

    return pydantic_field_to_value_mapping
