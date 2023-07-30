from __future__ import annotations

import asyncio
import functools
import sys

from contextlib import asynccontextmanager
from typing import Annotated

import aioboto3
import socketio
import structlog
import uvicorn

from beanie import init_beanie
from ddtrace.contrib.asgi import TraceMiddleware
from fastapi import FastAPI
from fastapi import Header
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST
from starlette_context import plugins
from starlette_context import request_cycle_context
from starlette_context.middleware import RawContextMiddleware

from src.api.v1 import create_root_router
from src.api.websockets import socketio_app
from src.config import app_config
from src.db.models import gather_documents
from src.exceptions import BusinessLogicError
from src.middlewares.logging_middleware import logging_middleware
from src.services.conversation_service import ConversationService
from src.services.relationship_service import RelationshipService
from src.services.user_service import UserService
from src.utils.custom_logging import setup_logging
from src.utils.socketio_utils import IdempotentSocketIOAsyncClient
from src.utils.stub import DependencyStub
from src.utils.stub import SingletonDependency


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    mongodb_client = AsyncIOMotorClient(str(app_config.db_url))
    socketio_client = IdempotentSocketIOAsyncClient(
        logger=app_config.debug, engineio_logger=app_config.debug
    )
    boto3_session = aioboto3.Session(
        aws_access_key_id=app_config.s3_access_key,
        aws_secret_access_key=app_config.s3_secret_key,
        region_name=app_config.s3_region_name,
    )

    lifespan_fn = functools.partial(lifespan, mongodb_client=mongodb_client)

    app = FastAPI(
        docs_url="/api/v1/docs",
        default_response_class=ORJSONResponse,
        redoc_url=None,
        debug=app_config.debug,
        title=app_config.openapi_title,
        description=app_config.openapi_description,
        license_info={
            "name": "GNU General Public License v3.0",
            "url": "https://www.gnu.org/licenses/gpl-3.0.en.html",
        },
        version=app_config.version,
        lifespan=lifespan_fn,
    )
    _setup_middlewares(app)

    app.mount("/ws", app=socketio_app, name="socketio")
    app.include_router(create_root_router())

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(
        BusinessLogicError, transform_business_logic_exception_handler
    )

    app.dependency_overrides = {
        DependencyStub("user_service"): lambda: UserService(
            mongodb_client, boto3_session
        ),
        DependencyStub("contact_service"): lambda: RelationshipService(mongodb_client),
        DependencyStub("conversation_service"): lambda: ConversationService(
            mongodb_client
        ),
        DependencyStub("socketio_client"): SingletonDependency(socketio_client),
        DependencyStub("boto3_session"): SingletonDependency(boto3_session),
    }

    return app


def _setup_middlewares(app: FastAPI) -> None:
    app.middleware("http")(logging_middleware)

    # This middleware must be placed after the logging, to populate the context with the request ID
    # Middlewares are applied in the reverse order of when they are added (you can verify this
    # by debugging `app.middleware_stack` and recursively drilling down the `app` property).
    app.add_middleware(
        RawContextMiddleware,
        plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
    )

    # UGLY HACK
    # Datadog's `TraceMiddleware` is applied as the very first middleware in the list, by patching `FastAPI` constructor.
    # Unfortunately that means that it is the innermost middleware, so the trace/span are created last in the middleware
    # chain. Because we want to add the trace_id/span_id in the access log, we need to extract it from the middleware list,
    # put it back as the outermost middleware, and rebuild the middleware stack.
    # TODO: Open an issue in dd-trace-py to ask if it can change its initialization, or if there is an easy way to add the
    #       middleware manually, so we can add it later in the chain and have it be the outermost middleware.
    # TODO: Open an issue in Starlette to better explain the order of middlewares
    tracing_middleware = next(
        (m for m in app.user_middleware if m.cls == TraceMiddleware), None
    )
    if tracing_middleware is not None:
        app.user_middleware = [
            m for m in app.user_middleware if m.cls != TraceMiddleware
        ]
        structlog.stdlib.get_logger("api.datadog_patch").info(
            "Patching Datadog tracing middleware to be the outermost middleware..."
        )
        app.user_middleware.insert(0, tracing_middleware)
        app.middleware_stack = app.build_middleware_stack()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )


async def provide_additional_headers_to_openapi(
    x_request_id: Annotated[str, Header(...)],
    x_correlation_id: Annotated[str, Header(...)],
):
    data = {"x_request_id": x_request_id, "x_correlation_id": x_correlation_id}
    with request_cycle_context(data):
        yield


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | ValidationError
):
    data = {"detail": exc.errors()}

    if isinstance(exc, RequestValidationError):
        data["body"] = exc.body

    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(data),
    )


async def transform_business_logic_exception_handler(
    request: Request, exc: BusinessLogicError
):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"detail": exc.message}),
    )


@asynccontextmanager
async def lifespan(application: FastAPI, mongodb_client: AsyncIOMotorClient):
    logger.info("Trying to init beanie and connect to MongoDB...")
    try:
        async with asyncio.timeout(5):
            await init_beanie(
                database=getattr(mongodb_client, app_config.database_name),
                document_models=gather_documents(),
            )
    except asyncio.TimeoutError:
        logger.error(
            "Failed to connect to MongoDB within 5 seconds. "
            "Check credentials of mongodb and is the mongodb instance running Exiting application..."
        )
        sys.exit(1)
    yield
    socketio_client: socketio.AsyncClient = application.dependency_overrides[
        DependencyStub("socketio_client")
    ]()
    await socketio_client.disconnect()


app = create_app()

if __name__ == "__main__":
    setup_logging(json_logs=not app_config.debug, log_level=app_config.logging_level)
    uvicorn.run(
        app="main:app", reload=True, host="localhost", port=5001, access_log=False
    )
