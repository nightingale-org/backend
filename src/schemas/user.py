from __future__ import annotations

from datetime import datetime

from beanie import PydanticObjectId
from fastapi import UploadFile
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field
from pydantic import field_validator

from src.utils.pydantic_utils import Username


class UserInputSchema(BaseModel):
    username: Username = None
    bio: str = None
    email: EmailStr
    email_verified_at: datetime | None = None
    image: str = None


class UserUpdateSchema(BaseModel):
    username: Username | None
    bio: str | None
    image: UploadFile | None


class CheckUsernameAvailabilitySchema(BaseModel):
    username: str


class ExistsResponseSchema(BaseModel):
    exists: bool


class UserOutputSchema(BaseModel):
    id: str
    bio: str | None = None
    username: Username | None = None
    email: EmailStr
    email_verified: datetime | None = None
    image: str = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_object_id(cls, value: PydanticObjectId) -> str:
        return str(value)


class AccountScheme(BaseModel):
    user_id: str = Field(alias="userId")
    provider_name: str = Field(alias="type")
    provider_account_id: str = Field(alias="providerAccountId")
    refresh_token: str | None = None
    access_token: str | None = None
    access_token_expires: datetime | None = None
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    # TODO update on update
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)
    expires_at: int | None = None
    token_type: str | None = None
    scope: str | None = None
    id_token: str | None = None
    session_state: str | None = None
