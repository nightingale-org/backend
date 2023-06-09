from __future__ import annotations

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter
from fastapi import Depends
from socketio.asyncio_client import AsyncClient

from src.schemas.conversations import CreateConversationSchema
from src.services.conversation_service import ConversationService
from src.utils.auth import UserCredentials
from src.utils.auth import get_current_user_credentials
from src.utils.auth import validate_jwt_token
from src.utils.socketio_utils import emit_on_connect
from src.utils.stub import DependencyStub


router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(validate_jwt_token)],
)


@router.get("/")
async def get_conversations(
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    return await conversation_service.get_all_conversations(user_credentials.email)


@router.put("/")
async def create_conversation(
    conversation_input: CreateConversationSchema,
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
    socketio_client: Annotated[AsyncClient, Depends(DependencyStub("socketio_client"))],
):
    conversation = await conversation_service.create_conversation(conversation_input)
    await emit_on_connect(
        socketio_client, "conversations:new", conversation.json(by_alias=True)
    )
    return conversation


@router.get("/{conversation_id}")
async def get_conversation_by_id(
    conversation_id: PydanticObjectId,
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
):
    return await conversation_service.get_conversation(conversation_id)
