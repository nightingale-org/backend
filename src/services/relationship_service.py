from __future__ import annotations

from beanie import PydanticObjectId, WriteRules
from beanie.odm.operators.update.general import Set

from src.db.models import User
from src.db.models.relationship import Relationship, RelationshipType
from src.exceptions import BusinessLogicException
from src.services.base_service import BaseService


class RelationshipService(BaseService):
    async def get_relationships(
        self, contact_type: RelationshipType, email: str, limit: int = 20
    ):
        return (
            await Relationship.find(Relationship.type == contact_type)
            .find({"user.email": email}, fetch_links=True)
            .limit(limit)
            .to_list()
        )

    async def add_relationship(self, username: str, *, initiator_email: str):
        relationship_partner = await User.find_one(
            User.username == username, session=self._current_session
        )
        if not relationship_partner:
            raise BusinessLogicException(
                f"Could not locate a user by the username {username}."
            )

        initiator = await User.find_one(
            User.email == initiator_email, session=self._current_session
        )
        if initiator.id == relationship_partner.id:
            raise BusinessLogicException("You can't add yourself to relationships")

        await initiator.fetch_link("relationships")

        for contact in initiator.relationships:
            if contact.user.id == relationship_partner.id:
                raise BusinessLogicException(
                    f"User {relationship_partner.username} is already in your contacts."
                )

        initiator.relationships.append(
            Relationship(
                with_user=relationship_partner, type=RelationshipType.established
            )
        )
        await initiator.save(link_rule=WriteRules.WRITE, session=self._current_session)

    async def block_user(self, *, initiator_user_id: str, partner_user_id: str) -> None:
        await Relationship.find_one(
            Relationship.with_user.id == PydanticObjectId(partner_user_id),
            Relationship.initiator.email == initiator_user_id,
            fetch_links=True,
            session=self._current_session,
        ).update_one(
            Set({Relationship.type: RelationshipType.blocked}),
            session=self._current_session,
        )
