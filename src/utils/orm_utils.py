from __future__ import annotations

from typing import Any

from beanie import Document
from bson import ObjectId


def compare_id(column: Any, value: str) -> bool:
    """
    In order to accurately compare the value with the id column, it is necessary to explicitly cast it to ObjectId.
    Without doing so, the comparison will not function properly. To prevent errors within the code and reduce its susceptibility to mistakes,
    it is recommended to utilize this helper for comparing the id column with a string value.
    """
    # TODO: create issue in the beanie repo
    return column == ObjectId(value)


def get_collection_name_from_model(model: type[Document]) -> str:
    return model.get_settings().name or model.__name__.lower()
