from __future__ import annotations


class BusinessLogicException(Exception):
    def __init__(self, message: str):
        self.message = message
