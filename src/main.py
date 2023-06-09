from __future__ import annotations

import functools

from contextlib import asynccontextmanager
from typing import Annotated

import socketio
import uvicorn

from beanie import init_beanie
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
from src.services.conversation_service import ConversationService
from src.services.relationship_service import RelationshipService
from src.services.user_service import UserService
from src.utils.logs import configure_logging
from src.utils.socketio_utils import IdempotentAsyncClient
from src.utils.stub import DependencyStub
from src.utils.stub import SingletonDependency


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
    await init_beanie(
        database=getattr(mongodb_client, app_config.database_name),
        document_models=gather_documents(),
    )
    yield
    socketio_client: socketio.AsyncClient = application.dependency_overrides[
        DependencyStub("socketio_client")
    ]()
    await socketio_client.disconnect()


def create_app() -> FastAPI:
    mongodb_client = AsyncIOMotorClient(str(app_config.db_url))
    socketio_client = IdempotentAsyncClient(
        logger=app_config.debug, engineio_logger=app_config.debug
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

    app.mount("/ws", app=socketio_app, name="socketio")
    app.add_middleware(
        RawContextMiddleware,
        plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.include_router(create_root_router())

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(
        BusinessLogicError, transform_business_logic_exception_handler
    )

    app.dependency_overrides = {
        DependencyStub("user_service"): lambda: UserService(mongodb_client),
        DependencyStub("contact_service"): lambda: RelationshipService(mongodb_client),
        DependencyStub("conversation_service"): lambda: ConversationService(
            mongodb_client
        ),
        DependencyStub("socketio_client"): SingletonDependency(socketio_client),
    }

    return app


app = create_app()

if __name__ == "__main__":
    configure_logging()
    uvicorn.run(app="main:app", reload=True, host="localhost", port=8000)
