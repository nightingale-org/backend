from __future__ import annotations

import asyncio
import datetime
import functools
import sys

from contextlib import asynccontextmanager
from typing import Annotated

import aioboto3
import redis.exceptions
import socketio
import structlog
import uvicorn

from beanie import init_beanie
from bson import CodecOptions
from ddtrace.contrib.asgi import TraceMiddleware
from fastapi import FastAPI
from fastapi import Header
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio.client import Redis
from rodi import Container
from rodi import Services
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST
from starlette_context import plugins
from starlette_context import request_cycle_context
from starlette_context.middleware import RawContextMiddleware

from src.api.v1 import create_root_router
from src.api.websockets.server import asgi_app
from src.api.websockets.server import socketio_server
from src.config import app_config
from src.db.models import gather_documents
from src.exceptions import BusinessLogicError
from src.middlewares.logging_middleware import logging_middleware
from src.services.conversation_service import ConversationService
from src.services.relationship_service import RelationshipService
from src.services.relationship_stats_service import RelationshipStatsService
from src.services.user_service import UserService
from src.utils.custom_logging import setup_logging
from src.utils.socketio.socket_manager import SocketIOManager
from src.utils.stub import DependencyStub
from src.utils.stub import SingletonDependency


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    mongodb_client = AsyncIOMotorClient(str(app_config.db_url))
    socketio_manager = SocketIOManager(
        socketio.AsyncRedisManager(str(app_config.redis_dsn), write_only=True)
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

    # Setup dependency injection using third-party library for SocketIO
    # since it doesn't support it out of the box and
    # one can't really use FastAPI's dependency injection system for it
    container = Container()
    container.add_instance(RelationshipStatsService(mongodb_client))
    container.add_instance(UserService(mongodb_client, boto3_session))
    provider = container.build_provider()
    _mount_websocket_app(app, provider)

    app.include_router(create_root_router())

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(
        BusinessLogicError, transform_business_logic_exception_handler
    )

    app.dependency_overrides = {
        DependencyStub("user_service"): lambda: UserService(
            mongodb_client, boto3_session
        ),
        DependencyStub("relationship_service"): lambda: RelationshipService(
            mongodb_client, socketio_manager
        ),
        DependencyStub("conversation_service"): lambda: ConversationService(
            mongodb_client
        ),
        DependencyStub("boto3_session"): SingletonDependency(boto3_session),
    }

    return app


def _mount_websocket_app(app: FastAPI, services: Services):
    # TODO: Find a better way of doing it through an instance variable
    # TODO: It might cause a memory leak later on!!!
    # For now, this is how the most basic dependency injection is implemented in SocketIO
    socketio_server.services = services
    app.mount("/ws", app=asgi_app, name="socketio")


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
        allow_origins=["http://localhost:8080", "http://localhost:3000"],
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


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    data = {"detail": exc.errors(), "body": exc.body}

    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(data),
    )


async def transform_business_logic_exception_handler(
    request: Request, exc: BusinessLogicError
):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"detail": exc.detail, "code": exc.code}),
    )


@asynccontextmanager
async def lifespan(application: FastAPI, mongodb_client: AsyncIOMotorClient):
    logger.info("Trying to connect to Redis and check if it's alive...")
    redis_instance = Redis.from_url(
        str(app_config.redis_dsn), socket_keepalive=True, socket_timeout=300
    )
    try:
        await redis_instance.ping()
    except redis.exceptions.ConnectionError:
        logger.error(
            "Failed to connect to Redis. Check credentials of redis and is the redis instance running. Exiting application..."
        )
        sys.exit(1)
    logger.info("Successfully connected to Redis.")

    logger.info("Trying to init beanie and connect to MongoDB...")
    try:
        async with asyncio.timeout(5):
            await init_beanie(
                database=mongodb_client.get_database(
                    app_config.database_name,
                    CodecOptions(tz_aware=True, tzinfo=datetime.UTC),
                ),
                document_models=gather_documents(),
            )
    except asyncio.TimeoutError:
        logger.error(
            "Failed to connect to MongoDB within 5 seconds. "
            "Check credentials of mongodb and is the mongodb instance running Exiting application..."
        )
        sys.exit(1)
    logger.info("Successfully connected to MongoDB and initialized beanie")
    yield


app = create_app()

if __name__ == "__main__":
    setup_logging(json_logs=not app_config.debug, log_level=app_config.logging_level)
    uvicorn.run(
        app="main:app", reload=True, host="localhost", port=5001, access_log=False
    )
