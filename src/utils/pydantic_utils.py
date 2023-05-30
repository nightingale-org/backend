from typing import Any, Dict, Optional, Type, TypeVar

import pydantic
from beanie import Document
from pydantic.fields import ModelField

_T = TypeVar("_T", bound=Any)


def map_raw_data_to_pydantic_fields(
    data: Dict[str, _T], document_type: Type[Document]
) -> Dict[ModelField, _T]:
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
