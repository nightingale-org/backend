from __future__ import annotations


class BusinessLogicError(Exception):
    def __init__(self, detail: str, code: str):
        self.detail = detail
        self.code = code
