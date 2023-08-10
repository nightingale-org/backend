from __future__ import annotations

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter
from fastapi import Depends

from src.schemas.conversations import CreateConversationSchema
from src.services.conversation_service import ConversationService
from src.utils.auth import UserCredentials
from src.utils.auth import get_current_user_credentials
from src.utils.auth import validate_jwt_token
from src.utils.stub import DependencyStub


router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(validate_jwt_token)],
)


@router.get("/", response_model_by_alias=True)
async def get_conversations(
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    return await conversation_service.get_all_conversations(user_credentials.email)


@router.put("/", response_model_by_alias=True)
async def create_conversation(
    conversation_input: CreateConversationSchema,
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
):
    conversation = await conversation_service.create_conversation(conversation_input)
    return conversation


@router.get("/{conversation_id}", response_model_by_alias=True)
async def get_conversation_by_id(
    conversation_id: PydanticObjectId,
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
):
    return await conversation_service.get_conversation(conversation_id)
