from __future__ import annotations

import functools
import inspect

from collections.abc import Callable
from typing import Any
from typing import Concatenate
from typing import ParamSpec
from typing import TypeVar

import socketio.exceptions

from pydantic import BaseModel
from pydantic import ValidationError
from starlette.requests import Request


T = TypeVar("T")
P = ParamSpec("P")

CallableT = TypeVar("CallableT", bound=Callable[..., Any])


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
