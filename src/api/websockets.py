from __future__ import annotations

from typing import NoReturn

import socketio.exceptions
import structlog

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from src.config import app_config
from src.db.models import Conversation
from src.db.models import Message
from src.utils.auth import TokenInvalidError
from src.utils.auth import get_current_user_credentials
from src.utils.auth import get_token_payload
from src.utils.auth import token_auth_scheme
from src.utils.socketio_utils import validate_data
from src.utils.socketio_utils import with_request


client_manager = socketio.AsyncRedisManager(str(app_config.redis_dsn))
socketio_server = socketio.AsyncServer(
    async_mode="asgi",
    # this is very important to set it to empty list since CORS is handled by FastAPI, and we don't want to mess with it
    cors_allowed_origins=[],
    logger=True,
    engineio_logger=True,
    client_manager=client_manager,
)
socketio_app = socketio.ASGIApp(socketio_server=socketio_server)
logger = structlog.get_logger(__name__)

_EMAIL_TO_SID_USERS_MAP: dict[str, str] = {}


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

    async with socketio_server.session(sid) as session:
        session["user_credentials"] = user_credentials

    await client_manager.redis.set(f"socketio:email:sid:{user_credentials.email}", sid)


@socketio_server.event
async def disconnect(sid: str):
    async with socketio_server.session(sid) as session:
        email = session["user_credentials"].email
        await client_manager.redis.delete(f"socketio:email:sid:{email}")


@socketio_server.on("conversations:new")
@validate_data(pydantic_model=Conversation)
async def new_conversation(sid: str, _, parsed_data: Conversation):
    async with socketio_server.session(sid) as session:
        user_creds = session["user_credentials"]

    conversation = parsed_data
    for member in conversation.members:
        email = member.email
        if email not in _EMAIL_TO_SID_USERS_MAP or email == user_creds.email:
            continue

        await socketio_server.emit(
            "conversations:new", conversation.dict(), to=_EMAIL_TO_SID_USERS_MAP[email]
        )


@socketio_server.on("messages:new")
@validate_data(pydantic_model=Message)
async def on_new_message(sid: str, _, parsed_data: Message):
    async with socketio_server.session(sid) as session:
        user_creds = session["user_credentials"]
    message = parsed_data

    for member in message.conversation.members:
        email = member.email
        if email not in _EMAIL_TO_SID_USERS_MAP or email == user_creds.email:
            continue

        await socketio_server.emit(
            "messages:new", message.dict(), to=_EMAIL_TO_SID_USERS_MAP[email]
        )
