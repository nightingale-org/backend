from __future__ import annotations

import asyncio
import functools
import inspect

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from typing import Concatenate
from typing import ParamSpec
from typing import TypeVar

import socketio.exceptions
import structlog

from pydantic import BaseModel
from pydantic import ValidationError
from starlette.requests import Request


T = TypeVar("T")
P = ParamSpec("P")

CallableT = TypeVar("CallableT", bound=Callable[..., Any])


@dataclass
class SocketIOManagerError(Exception):
    message: str
    event_name: str
    target: Any

    def __str__(self) -> str:
        return f"An error occurred when trying to send an event {self.event_name} to {self.target}: {self.message}"


class SocketIOManager:
    def __init__(self, native_client_manager: socketio.AsyncRedisManager):
        self._native_client_manager = native_client_manager
        self._logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

    async def emit_to_user_by_email(
        self,
        email: str,
        event_name: str,
        payload: BaseModel,
        *,
        raise_on_not_connected: bool = True,
    ):
        self._logger.info(
            "Emitting event to user by email", email=email, event_name=event_name
        )
        target_sid = await self._native_client_manager.redis.get(
            f"socketio:email:sid:{email}"
        )
        if target_sid is None and raise_on_not_connected:
            raise SocketIOManagerError(
                message="User is not connected to socketio",
                event_name=event_name,
                target=email,
            )

        if isinstance(target_sid, bytes):
            target_sid = target_sid.decode("utf-8")

        await self._native_client_manager.emit(
            event_name, payload.model_dump(mode="json"), room=target_sid
        )
        self._logger.info(
            "Event was successfully emitted to the client",
            email=email,
            sid=target_sid,
            event_name=event_name,
        )

    async def emit_to_users_in_bulk(
        self,
        *emails: str,
        event_name: str,
        payload: BaseModel,
        raise_on_not_connected: bool = True,
    ):
        sids: list[str | bytes | None] = await asyncio.gather(
            *[
                self._native_client_manager.redis.get(f"socketio:email:sid:{email}")
                for email in emails
            ]
        )

        none_sids = [sid for sid in sids if sid is None]
        if none_sids and raise_on_not_connected:
            raise SocketIOManagerError(
                message="Some users are not connected to socketio",
                event_name=event_name,
                target=none_sids,
            )
        sids = [
            sid.decode("utf-8")
            for sid in sids
            if sid is not None and isinstance(sid, bytes)
        ]

        await asyncio.gather(
            *[
                self._native_client_manager.emit(
                    event_name, payload.model_dump(mode="json"), room=sid
                )
                for sid in sids
            ]
        )


def with_request(func: Callable[P, T]) -> Callable[Concatenate[Request, P], T]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        environ: dict[str, Any] = args[1]
        request = Request(
            environ["asgi.scope"], environ["asgi.receive"], environ["asgi.send"]
        )

        args = _trim_arguments(func, args, number_of_reserved_arguments=1)
        return await func(request, *args, **kwargs)

    return wrapper


def validate_data(
    *,
    pydantic_model: type[BaseModel],
    validation_exception: type[Exception] = socketio.exceptions.ConnectionRefusedError,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            data = args[1]
            try:
                if isinstance(data, str | bytes):
                    parsed_data = pydantic_model.parse_raw(data)
                elif isinstance(data, dict):
                    parsed_data = pydantic_model.parse_obj(data)
                else:
                    raise ValueError(
                        f"Data must be either a string, bytes or dict, got {type(data)}"
                    )
            except ValidationError as ex:
                raise validation_exception(ex.json()) from ex

            args = _trim_arguments(func, args, should_accept_at_least=2)

            # The handler still has to accept the data argument as it's used internally in python-socketio
            # So the only solution that I've come up with is to pass the parsed data as a keyword argument
            return await func(
                args[0], data, *args[2:], **{**kwargs, "parsed_data": parsed_data}
            )

        return wrapper

    return decorator


def _trim_arguments(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    *,
    should_accept_at_least: int = float("-inf"),
    number_of_reserved_arguments: int = 0,
) -> tuple[Any, ...]:
    """Cut off arguments that are not declared in the function signature"""
    spec = inspect.getfullargspec(func)
    arguments_that_function_really_accept = args[
        : len(spec.args) - number_of_reserved_arguments
    ]

    if len(arguments_that_function_really_accept) < should_accept_at_least:
        raise ValueError(
            f"Function {func.__name__} accepts less arguments than expected. "
            f"Args = {args}, should accept at least {should_accept_at_least}"
        )

    return arguments_that_function_really_accept
