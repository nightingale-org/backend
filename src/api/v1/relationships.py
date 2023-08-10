from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from pydantic import PositiveInt
from starlette import status
from starlette.responses import Response
from starlette.status import HTTP_200_OK
from starlette.status import HTTP_201_CREATED

from src.db.models.relationship import RelationshipType
from src.schemas.relationship import BlockUserSchema
from src.schemas.relationship import FriendRequestPayload
from src.schemas.relationship import RelationshipListItemSchema
from src.schemas.relationship import UpdateRelationshipStatusPayload
from src.services.relationship_service import RelationshipService
from src.utils.auth import UserCredentials
from src.utils.auth import get_current_user_credentials
from src.utils.auth import validate_jwt_token
from src.utils.depends import int_enum_query
from src.utils.stub import DependencyStub


router = APIRouter(
    prefix="/relationships",
    tags=["relationships"],
    dependencies=[Depends(validate_jwt_token)],
)


@router.get(
    "/", response_model_by_alias=False, response_model=list[RelationshipListItemSchema]
)
async def get_relationships(
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("relationship_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
    relationship_type: Annotated[
        RelationshipType,
        Depends(
            int_enum_query("type", RelationshipType, default=RelationshipType.settled)
        ),
    ],
    limit: PositiveInt = 20,
):
    return await relationship_service.get_relationships(
        relationship_type=relationship_type,
        email=user_credentials.email,
        limit=limit,
    )


@router.put("/", status_code=HTTP_201_CREATED)
async def send_friend_request(
    response: Response,
    friend_request_payload: FriendRequestPayload,
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("relationship_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    await relationship_service.create_friend_request(
        username=friend_request_payload.username, initiator_email=user_credentials.email
    )

    response.status_code = HTTP_201_CREATED
    return


@router.post("/update", status_code=status.HTTP_204_NO_CONTENT)
async def update_relationship_status(
    update_relationship_status_payload: UpdateRelationshipStatusPayload,
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("relationship_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    await relationship_service.update_relationship_status(
        update_relationship_status_payload,
        user_credentials.email,
    )


@router.post("/block", status_code=HTTP_200_OK)
async def block_user(
    block_user_payload: BlockUserSchema,
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("relationship_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    await relationship_service.block_user(
        initiator_user_id=user_credentials.email,
        partner_user_id=block_user_payload.user_id,
    )
    return Response(status_code=HTTP_200_OK)
