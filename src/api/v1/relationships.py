from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import PositiveInt, parse_obj_as
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from src.db.models.relationship import RelationshipType
from src.schemas.relationship import (
    BlockUserSchema,
    CreateRelationshipInputSchema,
    RelationshipSchema,
)
from src.services.relationship_service import RelationshipService
from src.utils.auth import (
    UserCredentials,
    get_current_user_credentials,
    validate_jwt_token,
)
from src.utils.stub import DependencyStub

router = APIRouter(
    prefix="/contacts", tags=["contacts"], dependencies=[Depends(validate_jwt_token)]
)


@router.get("/")
async def get_relationships(
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("contact_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
    relationship_type: RelationshipType = Query(
        default=RelationshipType.established, alias="type"
    ),
    limit: PositiveInt = 20,
) -> list[RelationshipSchema]:
    # TODO: replace parse_obj_as with ContactSchema.construct with list comprehension
    # to optimize performance since we don't need to revalidate the data from odm.
    return parse_obj_as(
        list[RelationshipSchema],
        await relationship_service.get_relationships(
            contact_type=relationship_type, email=user_credentials.email, limit=limit
        ),
    )


@router.put("/", status_code=HTTP_201_CREATED)
async def add_relationship(
    relationship_payload: CreateRelationshipInputSchema,
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("contact_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    await relationship_service.add_relationship(
        username=relationship_payload.username, initiator_email=user_credentials.email
    )

    return Response(status_code=HTTP_201_CREATED)


@router.post("/block/", status_code=HTTP_200_OK)
async def block_user(
    block_user_payload: BlockUserSchema,
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("contact_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    await relationship_service.block_user(
        initiator_user_id=user_credentials.email,
        partner_user_id=block_user_payload.user_id,
    )
    return Response(status_code=HTTP_200_OK)
