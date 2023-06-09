from __future__ import annotations


class BusinessLogicError(Exception):
    def __init__(self, message: str):
        self.message = message
