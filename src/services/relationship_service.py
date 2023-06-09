from __future__ import annotations

from beanie import PydanticObjectId
from beanie.odm.operators.update.general import Set

from src.db.models import User
from src.db.models.relationship import Relationship
from src.db.models.relationship import RelationshipType
from src.exceptions import BusinessLogicError
from src.services.base_service import BaseService


class RelationshipService(BaseService):
    async def get_relationships(
        self, contact_type: RelationshipType, email: str, limit: int = 20
    ) -> list[Relationship]:
        return (
            await Relationship.find(Relationship.type == contact_type)
            .aggregate(
                [
                    {
                        "$lookup": {
                            "from": User.get_settings().name,
                            "localField": "initiator_id",
                            "foreignField": "_id",
                            "as": "initiator",
                        }
                    },
                    {
                        "$match": {
                            "initiator.email": email,
                        }
                    },
                ]
            )
            .limit(limit)
            .to_list()
        )

    async def establish_relationship(self, username: str, *, initiator_email: str):
        relationship_partner = await User.find_one(
            User.username == username, session=self._current_session
        )
        if not relationship_partner:
            raise BusinessLogicError(
                f"Could not locate a user by the username {username}."
            )

        initiator = await User.find_one(
            User.email == initiator_email, session=self._current_session
        )
        if initiator.id == relationship_partner.id:
            raise BusinessLogicError("You can't add yourself to relationships")

        await Relationship(
            initiator_id=initiator.id, partner=relationship_partner
        ).create(session=self._current_session)

    async def block_user(self, *, initiator_user_id: str, partner_user_id: str) -> None:
        await Relationship.find_one(
            Relationship.partner.id == PydanticObjectId(partner_user_id),
            Relationship.initiator.email == initiator_user_id,
            fetch_links=True,
            session=self._current_session,
        ).update_one(
            Set({Relationship.type: RelationshipType.blocked}),
            session=self._current_session,
        )
