from __future__ import annotations

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import PositiveInt
from starlette.status import HTTP_404_NOT_FOUND

from src.schemas.conversations import ConversationPreviewSchema
from src.schemas.conversations import ConversationPreviewSchemaCursorPayload
from src.schemas.conversations import CreateConversationSchema
from src.schemas.pagination import PaginatedResponse
from src.services.conversation_service import ConversationService
from src.utils.auth import UserCredentials
from src.utils.auth import get_current_user_credentials
from src.utils.auth import validate_jwt_token
from src.utils.pagination import pagination
from src.utils.stub import DependencyStub


router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(validate_jwt_token)],
)


@router.get(
    "/",
    response_model_by_alias=False,
    response_model=PaginatedResponse[ConversationPreviewSchema],
)
async def get_conversation_previews(
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
    limit: Annotated[PositiveInt, Query(le=50, ge=10)] = 10,
    next_cursor_payload: Annotated[
        ConversationPreviewSchemaCursorPayload | None,
        Depends(
            pagination(
                ConversationPreviewSchemaCursorPayload, "conversation", default=None
            )
        ),
    ] = None,
):
    paginated_result = await conversation_service.get_conversation_previews(
        user_credentials.email, limit=limit, cursor_payload=next_cursor_payload
    )

    return PaginatedResponse[ConversationPreviewSchema].from_paginated_result(
        paginated_result
    )


@router.put("/", response_model_by_alias=True)
async def create_conversation(
    conversation_input: CreateConversationSchema,
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
):
    conversation = await conversation_service.create_conversation(conversation_input)
    return conversation


@router.get(
    "/{conversation_id}",
    response_model_by_alias=False,
    response_model=ConversationPreviewSchema,
)
async def get_conversation_preview_by_id(
    conversation_id: PydanticObjectId,
    conversation_service: Annotated[
        ConversationService, Depends(DependencyStub("conversation_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    conversation_preview = await conversation_service.get_conversation_preview_by_id(
        conversation_id, user_credentials.email
    )
    if conversation_preview is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    return conversation_preview
