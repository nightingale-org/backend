from typing import Any, Dict, Type, TypeVar

from beanie import Document
from pydantic.fields import ModelField

_T = TypeVar("_T", bound=Any)


def map_raw_data_to_pydantic_fields(
    data: Dict[str, _T], document_type: Type[Document]
) -> Dict[ModelField, _T]:
    pydantic_field_to_value_mapping = {}
    for key in data:
        if key not in document_type.__fields__:
            # TODO write more descriptive error message
            raise Exception("Invalid field")

        pydantic_field_to_value_mapping[document_type.__fields__[key]] = data[key]

    return pydantic_field_to_value_mapping
