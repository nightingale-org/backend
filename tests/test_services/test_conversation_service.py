from __future__ import annotations

import pytest

from faker import Faker
from pydantic import ValidationError

from src.db.models import User
from src.services.conversation_service import ConversationService


pytestmark = pytest.mark.anyio


@pytest.fixture
def conversation_service(motor_client):
    return ConversationService(motor_client)


@pytest.fixture(autouse=True)
def set_random_seed(faker: Faker):
    faker.random.seed()


async def test_create_conversation_with_one_user_raises_error(
    conversation_service, faker: Faker
):
    user = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user.create()

    with pytest.raises(
        ValidationError, match="Conversation has to have at least 2 members."
    ):
        await conversation_service.create_conversation(members=[user], is_group=False)


async def test_create_conversation_with_no_users_raises_error(conversation_service):
    with pytest.raises(
        ValidationError, match="Conversation has to have at least 2 members."
    ):
        await conversation_service.create_conversation(members=[], is_group=False)


async def test_create_conversation_with_two_users(conversation_service, faker: Faker):
    user1 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user1.create()
    user2 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user2.create()

    conversation = await conversation_service.create_conversation(
        members=[user1, user2], is_group=False
    )

    assert conversation.members == [user1, user2]
    assert conversation.is_group is False
    assert conversation.name is None
    assert conversation.user_limit is None
    assert conversation.created_at is not None
    assert conversation.messages == []
    assert conversation.id is not None


async def test_create_conversation_with_three_users(conversation_service, faker: Faker):
    user1 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user1.create()
    user2 = User(email=faker.unique.email())
    await user2.create()
    user3 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user3.create()

    conversation = await conversation_service.create_conversation(
        members=[user1, user2, user3], is_group=True
    )

    assert conversation.members == [user1, user2, user3]
    assert conversation.is_group is True
    assert conversation.name is None
    assert conversation.user_limit is None
    assert conversation.created_at is not None
    assert conversation.messages == []
    assert conversation.id is not None


async def test_get_all_conversations(conversation_service, faker: Faker):
    user1 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user1.create()
    user2 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user2.create()
    user3 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user3.create()

    conversation1 = await conversation_service.create_conversation(
        members=[user1, user2], is_group=False
    )
    conversation2 = await conversation_service.create_conversation(
        members=[user1, user3, user2], is_group=True
    )
    conversation3 = await conversation_service.create_conversation(
        members=[user2, user3], is_group=False
    )

    conversations = await conversation_service.get_conversation_previews(
        email=user1.email
    )

    assert len(conversations) == 2
    assert conversation1.id in (x.id for x in conversations)
    assert conversation2.id in (x.id for x in conversations)
    assert conversation3.id not in (x.id for x in conversations)


async def test_get_conversation_by_id(conversation_service, faker: Faker):
    user1 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user1.create()
    user2 = User(email=faker.unique.email(), username=faker.unique.user_name())
    await user2.create()
    conversation = await conversation_service.create_conversation(
        members=[user1, user2], is_group=False
    )

    assert await conversation_service.get_conversation(conversation.id) == conversation
