from __future__ import annotations

import asyncio

from typing import Any

import socketio
import structlog

from pydantic import BaseModel

from src.utils.socketio.exceptions import SocketIOManagerError


class SocketIOManager:
    def __init__(self, native_client_manager: socketio.AsyncRedisManager):
        self._native_client_manager = native_client_manager
        self._logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

    async def emit_to_user_by_email(
        self,
        email: str,
        event_name: str,
        payload: BaseModel | dict[str, Any],
        *,
        raise_if_recipient_not_connected: bool = True,
    ):
        self._logger.info(
            "Emitting event to user by email", email=email, event_name=event_name
        )
        target_sid = await self._native_client_manager.redis.get(
            f"socketio:email:sid:{email}"
        )
        if target_sid is None and raise_if_recipient_not_connected:
            raise SocketIOManagerError(
                message="User is not connected to socketio",
                event_name=event_name,
                target=email,
            )

        if isinstance(target_sid, bytes):
            target_sid = target_sid.decode("utf-8")

        if isinstance(payload, BaseModel):
            payload = payload.model_dump(mode="json")

        await self._native_client_manager.emit(event_name, payload, room=target_sid)
        self._logger.info(
            "Event was successfully emitted to the client",
            email=email,
            sid=target_sid,
            event_name=event_name,
        )

    async def emit_to_user_in_bulk(
        self,
        email: str,
        event_names: list[str],
        payload: list[BaseModel | dict[str, Any]],
        raise_on_not_connected: bool = True,
    ):
        return await asyncio.gather(
            *[
                self.emit_to_user_by_email(
                    email,
                    event_name,
                    payload,
                    raise_if_recipient_not_connected=raise_on_not_connected,
                )
                for (payload, event_name) in zip(payload, event_names, strict=True)
            ]
        )
