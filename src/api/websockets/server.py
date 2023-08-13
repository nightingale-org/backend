from __future__ import annotations

from typing import Literal
from typing import NoReturn

import socketio.exceptions
import structlog

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from src.config import app_config
from src.db.models import User
from src.schemas.websockets.relationships import RelationshipEventsSeenPayload
from src.services.relationship_stats_service import RelationshipStatsService
from src.services.user_service import UserService
from src.utils.auth import TokenInvalidError
from src.utils.auth import get_current_user_credentials
from src.utils.auth import get_token_payload
from src.utils.auth import token_auth_scheme
from src.utils.socketio.common import validate_data
from src.utils.socketio.common import with_request
from src.utils.socketio.server import AsyncSocketIOServer


client_manager = socketio.AsyncRedisManager(str(app_config.redis_dsn))
socketio_server = AsyncSocketIOServer(
    async_mode="asgi",
    # this is very important to set it to empty list since CORS is handled by FastAPI, and we don't want to mess with it
    cors_allowed_origins=[],
    logger=True,
    engineio_logger=True,
    client_manager=client_manager,
)
asgi_app = socketio.ASGIApp(socketio_server)
logger = structlog.get_logger(__name__)

SessionType = dict[Literal["user"], User]


@socketio_server.event
@with_request
async def connect(request: Request, sid: str) -> bool | NoReturn:
    try:
        authorization_header_data = await token_auth_scheme(request)
    except HTTPException as ex:
        logger.error(
            "Authorization header is not provided or invalid", extra={"sid": sid}
        )
        raise socketio.exceptions.ConnectionRefusedError(ex.detail) from ex

    try:
        user_credentials = get_current_user_credentials(
            token_payload=await get_token_payload(authorization_header_data.credentials)
        )
    except (ValidationError, TokenInvalidError) as ex:
        logger.error("The access token is invalid", extra={"sid": sid})
        detail = ex.json() if isinstance(ex, ValidationError) else ex.reason
        raise socketio.exceptions.ConnectionRefusedError(detail) from ex

    user_service = socketio_server.services.get(UserService)
    user = await user_service.get_user_by_email(user_credentials.email)
    if user is None:
        logger.error(
            "The user with the provided email does not exist",
            extra={"sid": sid, "email": user_credentials.email},
        )
        raise socketio.exceptions.ConnectionRefusedError(
            "Token payload is invalid: the user with the provided email does not exist."
        )

    async with socketio_server.session(sid) as session:
        session["user"] = user

    await client_manager.redis.set(f"socketio:email:sid:{user_credentials.email}", sid)


@socketio_server.event
async def disconnect(sid: str):
    async with socketio_server.session(sid) as session:  # type: SessionType
        email = session["user"].email
        await client_manager.redis.delete(f"socketio:email:sid:{email}")


@socketio_server.on("relationship:events_seen")
@validate_data(pydantic_model=RelationshipEventsSeenPayload)
async def on_relationship_events_seen(
    sid: str, _, parsed_data: RelationshipEventsSeenPayload
):
    async with socketio_server.session(sid) as session:  # type: SessionType
        user_id = session["user"].id

    service = socketio_server.services.get(RelationshipStatsService)
    await service.reset_relationship_stats(user_id, parsed_data.type)
