from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from pydantic import PositiveInt
from pydantic import parse_obj_as
from starlette.responses import Response
from starlette.status import HTTP_200_OK
from starlette.status import HTTP_201_CREATED

from src.db.models.relationship import RelationshipTypeFlags
from src.schemas.relationship import BlockUserSchema
from src.schemas.relationship import CreateRelationshipInputSchema
from src.schemas.relationship import RelationshipSchema
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


@router.get("/")
async def get_relationships(
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("contact_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
    relationship_type: Annotated[
        RelationshipTypeFlags,
        Depends(
            int_enum_query(
                "type", RelationshipTypeFlags, default=RelationshipTypeFlags.established
            )
        ),
    ],
    limit: PositiveInt = 20,
) -> list[RelationshipSchema]:
    return parse_obj_as(
        list[RelationshipSchema],
        await relationship_service.get_relationships(
            relationship_type_flags=relationship_type,
            email=user_credentials.email,
            limit=limit,
        ),
    )


@router.put("/", status_code=HTTP_201_CREATED)
async def establish_relationship(
    response: Response,
    relationship_payload: CreateRelationshipInputSchema,
    relationship_service: Annotated[
        RelationshipService, Depends(DependencyStub("contact_service"))
    ],
    user_credentials: Annotated[UserCredentials, Depends(get_current_user_credentials)],
):
    await relationship_service.establish_relationship(
        username=relationship_payload.username, initiator_email=user_credentials.email
    )
    response.status_code = HTTP_201_CREATED
    return


@router.post("/block", status_code=HTTP_200_OK)
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
