from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SocketIOManagerError(Exception):
    message: str
    event_name: str
    target: Any

    def __str__(self) -> str:
        return f"An error occurred when trying to send an event {self.event_name} to {self.target}: {self.message}"
