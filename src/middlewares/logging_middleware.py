from __future__ import annotations

import time

import structlog

from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette_context import context
from starlette_context.header_keys import HeaderKeys
from uvicorn.protocols.utils import get_path_with_query_string


access_logger = structlog.stdlib.get_logger("api.access")


async def logging_middleware(request: Request, call_next) -> Response:
    structlog.contextvars.bind_contextvars(
        request_id=context[HeaderKeys.request_id],
        correlation_id=context[HeaderKeys.correlation_id],
    )

    start_time = time.perf_counter_ns()
    # If the call_next raises an error, we still want to return our own 500 response,
    # so we can add headers to it (process time, request ID...)
    response = Response(status_code=HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        response = await call_next(request)
    except Exception:
        # TODO: Validate that we don't swallow exceptions (unit test?)
        structlog.stdlib.get_logger("api.error").exception("Uncaught exception")
        raise
    finally:
        process_time = time.perf_counter_ns() - start_time
        status_code = response.status_code
        url = get_path_with_query_string(request.scope)
        client_host = request.client.host
        client_port = request.client.port
        http_method = request.method
        http_version = request.scope["http_version"]
        # Recreate the Uvicorn access log format, but add all parameters as structured information
        access_logger.info(
            f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
            http={
                "url": str(request.url),
                "status_code": status_code,
                "method": http_method,
                "version": http_version,
            },
            network={"client": {"ip": client_host, "port": client_port}},
            duration_ms=process_time / 10**6,
        )
        response.headers["X-Process-Time"] = str(process_time / 10**9)
        return response  # noqa: B012
